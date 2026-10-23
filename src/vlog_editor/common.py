from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".mts", ".m4v", ".webm"}


def run(args: list[str]) -> str:
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args[0]}\n{result.stderr[-6000:]}")
    return result.stdout


def require_tools():
    for name in ("ffmpeg", "ffprobe"):
        if not shutil.which(name):
            raise ValueError(f"{name} is required. Install FFmpeg before running.")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def fingerprint(path):
    path = Path(path).resolve()
    # Full content hash: catches source replacement even when size and mtime are preserved.
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"path": str(path), "size": path.stat().st_size, "sha256": h.hexdigest()}


def local_file(value):
    if "://" in str(value):
        raise ValueError("Only local files are supported. External uploads/APIs require approval.")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"File does not exist: {path}")
    return path


def protect_output(destination, input_dir, sources=()):
    dest = Path(destination).resolve()
    source_root = Path(input_dir).resolve()
    if dest == source_root or source_root in dest.parents:
        raise ValueError("Writing inside input/ is forbidden.")
    if dest in [Path(s).resolve() for s in sources]:
        raise ValueError("Output must not overwrite a source file.")
    return dest


def probe(path):
    path = local_file(path)
    raw = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]))
    videos = [s for s in raw["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]
    if not videos:
        raise ValueError(f"No video stream: {path}")
    v = videos[0]
    rotation = float(v.get("tags", {}).get("rotate", 0))
    for side in v.get("side_data_list", []):
        if "rotation" in side:
            rotation = float(side["rotation"])
    width, height = int(v["width"]), int(v["height"])
    if round(rotation) % 180:
        width, height = height, width
    # Container duration may belong to a longer audio track; trim to video length.
    try:
        duration = float(v.get("duration", "nan"))
    except (TypeError, ValueError):
        duration = math.nan
    if not math.isfinite(duration) or duration <= 0:
        duration = float(raw.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError(f"Invalid video duration: {path}")
    return {"path": str(path), "duration": duration, "width": int(v["width"]), "height": int(v["height"]),
            "display_width": width, "display_height": height, "rotation": rotation,
            "orientation": "portrait" if height > width else "landscape" if width > height else "square",
            "color_transfer": v.get("color_transfer"), "color_primaries":v.get("color_primaries"),
            "video_stream": v["index"], "fps": v.get("avg_frame_rate"),
            "creation_time": v.get("tags", {}).get("creation_time", raw.get("format", {}).get("tags", {}).get("creation_time")),
            "audio": [{"index": a["index"], "codec": a.get("codec_name"), "sample_rate": a.get("sample_rate"),
                       "channels": a.get("channels"), "duration": a.get("duration")} for a in raw["streams"] if a["codec_type"] == "audio"],
            "raw_probe": raw}


def validate_target(value):
    if value is not None and (not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0):
        raise ValueError("target_seconds must be null (unlimited) or a finite positive number")
