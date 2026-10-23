from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from .photos import PHOTO_EXTENSIONS, analyze_photo
from .common import EXTENSIONS, digest, fingerprint, probe, protect_output, run, write_json


def phash(gray):
    block = cv2.dct(cv2.resize(gray, (32, 32)).astype(np.float32))[:8, :8].flatten()
    bits = block > np.median(block[1:])
    bits[0] = False
    return f"{sum(int(b) << i for i, b in enumerate(bits)):016x}"


def histogram(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
    return cv2.normalize(hist, hist).flatten()


def motion(gray, adjacent):
    points = cv2.goodFeaturesToTrack(gray, maxCorners=150, qualityLevel=.02, minDistance=8)
    if points is None or len(points) < 8:
        return {"motion": 0.0, "residual": 0.0, "tracked": 0}
    tracked, status, _ = cv2.calcOpticalFlowPyrLK(gray, adjacent, points, None)
    if tracked is None:
        return {"motion": 0.0, "residual": 0.0, "tracked": 0}
    valid = status.flatten() == 1
    a, b = points[valid].reshape(-1, 2), tracked[valid].reshape(-1, 2)
    if len(a) < 6:
        return {"motion": 0.0, "residual": 0.0, "tracked": len(a)}
    matrix, inliers = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC)
    flow = b - a
    scale = math.hypot(*gray.shape)
    if matrix is None:
        residual = np.linalg.norm(flow - np.median(flow, axis=0), axis=1)
    else:
        predicted = cv2.transform(a.reshape(-1, 1, 2), matrix).reshape(-1, 2)
        residual = np.linalg.norm(b - predicted, axis=1)
    return {"motion": float(np.linalg.norm(np.median(flow, axis=0)) / scale),
            "residual": float(np.median(residual) / scale), "tracked": len(a)}


def extract(source, stream, timestamp, target, color_filter=None):
    run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", f"{timestamp:.6f}", "-i", str(source),
         "-map", f"0:{stream}", "-frames:v", "1", "-vf", (color_filter+"," if color_filter else "")+"scale=640:360:force_original_aspect_ratio=decrease",
         "-update", "1", str(target)])
    image = cv2.imread(str(target))
    if image is None:
        raise ValueError(f"Could not extract frame at {timestamp}: {source}")
    return image


def contact_sheet(samples, destination):
    cols, tw, th = 4, 320, 206
    # Paginate rather than allocating an unbounded image for long recordings.
    pages = []
    for offset in range(0, len(samples), 40):
        group = samples[offset:offset + 40]
        canvas = np.full((math.ceil(len(group) / cols) * th, cols * tw, 3), 25, np.uint8)
        for i, sample in enumerate(group):
            frame = cv2.imread(sample["frame"])
            h, w = frame.shape[:2]
            factor = min(tw / w, 174 / h)
            frame = cv2.resize(frame, (int(w * factor), int(h * factor)))
            x, y = (i % cols) * tw, (i // cols) * th
            canvas[y:y + frame.shape[0], x:x + frame.shape[1]] = frame
            label = f'{sample["time"]:.1f}s sharp:{sample["sharpness"]:.0f}'
            cv2.putText(canvas, label, (x + 5, y + 194), cv2.FONT_HERSHEY_SIMPLEX, .5, (240, 240, 240), 1)
        path = destination / f"contact-{offset // 40 + 1:03}.jpg"
        cv2.imwrite(str(path), canvas)
        pages.append(str(path))
    return pages


def analyze(input_dir, work_dir, config):
    input_dir, work_dir = Path(input_dir).resolve(), Path(work_dir).resolve()
    protect_output(work_dir, input_dir)
    files = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    photo_files = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in PHOTO_EXTENSIONS)
    if not files and not photo_files:
        raise ValueError(f"No videos or supported photos found in {input_dir}.")
    # Resolving symlinks prevents derivative files overwriting an original through an alias.
    sources = [p.resolve() for p in files + photo_files]
    for source in sources:
        if source == work_dir or work_dir in source.parents:
            raise ValueError("work/ must not contain source files, including symlink targets.")
    work_dir.mkdir(parents=True, exist_ok=True)
    report = {"version": 1, "input_dir": str(input_dir), "config": config, "videos": [], "photos": [], "errors": []}
    for index, path in enumerate(files):
        print(f"Analyze {index + 1}/{len(files)}: {path.name}", flush=True)
        try:
            meta = probe(path)
            meta["kind"] = "video"
            meta["relative_path"] = str(path.relative_to(input_dir))
            meta["id"] = digest(meta["relative_path"])[:12]
            meta["fingerprint"] = fingerprint(path)
            dest = work_dir / "frames" / meta["id"]
            dest.mkdir(parents=True, exist_ok=True)
            color_filter = None
            if meta.get('color_transfer')=='arib-std-b67':
                from .color import display_lut,hdr_filter
                color_filter=hdr_filter(display_lut(work_dir/'hlg-to-sdr.cube'))
            samples, last_hist = [], None
            interval = float(config["sample_interval"])
            times = np.arange(0, max(.001, meta["duration"] - .2), interval)
            for i, t in enumerate(times):
                frame_path = dest / f"{i:05}.jpg"
                frame = extract(path, meta["video_stream"], float(t), frame_path, color_filter)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Three close observations distinguish abrupt motion from a smooth pan.
                flows = []
                previous = gray
                for delta in (.12, .24):
                    adjacent_path = dest / "motion.jpg"
                    adjacent = extract(path, meta["video_stream"], min(float(t) + delta, meta["duration"] - .05), adjacent_path, color_filter)
                    current = cv2.cvtColor(adjacent, cv2.COLOR_BGR2GRAY)
                    flows.append(motion(previous, current))
                    previous = current
                adjacent_path.unlink(missing_ok=True)
                hist = histogram(frame)
                change = 0.0 if last_hist is None else float(cv2.compareHist(last_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
                mean = float(np.mean(gray) / 255)
                # Abrupt magnitude change + nonrigid residual, not raw camera speed.
                shake = abs(flows[1]["motion"] - flows[0]["motion"]) + max(f["residual"] for f in flows)
                sample = {"time": round(float(t), 4), "frame": str(frame_path),
                          "sharpness": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                          "exposure": mean, "clipped_fraction": float(np.mean((gray < 8) | (gray > 247))),
                          "hash": phash(gray), "scene_change": change, "shake": shake,
                          "motion": float(np.mean([f["motion"] for f in flows])),
                          "tracked": min(f["tracked"] for f in flows)}
                samples.append(sample)
                last_hist = hist
            boundaries = [0.0] + [s["time"] for s in samples[1:] if s["scene_change"] >= config["scene_threshold"]] + [meta["duration"]]
            meta["scenes"] = [{"start": a, "end": b} for a, b in zip(boundaries, boundaries[1:])]
            meta["samples"] = samples
            meta["contact_sheets"] = contact_sheet(samples, dest)
            report["videos"].append(meta)
        except (ValueError, RuntimeError, cv2.error) as exc:
            report["errors"].append({"path": str(path), "error": str(exc)})
    for path in photo_files:
        try:
            photo_id = digest(str(path.relative_to(input_dir)))[:12]
            report["photos"].append(analyze_photo(path, input_dir, work_dir/"frames"/photo_id, config))
        except (ValueError, OSError, RuntimeError) as exc:
            report["errors"].append({"path":str(path),"error":str(exc)})
    if not report["videos"] and not report["photos"]:
        write_json(work_dir / "analysis.json", report)
        raise ValueError("All inputs failed analysis; see analysis/analysis.json.")
    write_json(work_dir / "analysis.json", report)
    return report
