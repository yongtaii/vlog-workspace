from __future__ import annotations

import math
from pathlib import Path

from .cache import ENGINE_VERSION
from .cards import validate_card
from .common import validate_target, digest, fingerprint, local_file, probe, protect_output, read_json, run, write_json


def validate_timeline(timeline):
    if timeline.get("version") != 1 or not timeline.get("clips"):
        raise ValueError("Timeline version 1 and at least one clip are required.")
    settings = timeline["settings"]
    validate_target(settings.get("target_seconds"))
    for key in ("width", "height", "fps", "sample_interval", "clip_seconds", "max_shake"):
        value = settings[key]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Invalid positive setting: {key}")
    for key in ("width", "height"):
        if not isinstance(settings[key], int) or settings[key] % 2:
            raise ValueError("Output dimensions must be positive even integers.")
    if settings["transition"] not in ("cut", "fade"):
        raise ValueError("transition must be cut or fade (dip to black).")
    for key in ("music_volume", "source_volume", "transition_seconds", "min_sharpness"):
        if not math.isfinite(settings[key]) or settings[key] < 0:
            raise ValueError(f"Invalid setting: {key}")
    color = settings["color"]
    for key in ("contrast", "brightness", "saturation"):
        if not isinstance(color[key], (int, float)) or not math.isfinite(color[key]):
            raise ValueError(f"Color setting must be finite: {key}")
    if settings["preset"] not in {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow", "placebo"}:
        raise ValueError("Invalid x264 preset")
    if not isinstance(settings["subtitle_size"], int) or settings["subtitle_size"] <= 0:
        raise ValueError("subtitle_size must be a positive integer")
    for key in ("music", "font", "title_font"):
        if settings.get(key):
            local_file(settings[key])
    if not 0 <= settings["crf"] <= 51:
        raise ValueError("crf must be between 0 and 51.")
    ids = [c["id"] for c in timeline["clips"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Clip IDs must be unique for safe revisions")
    position = 0.
    for clip in timeline["clips"]:
        source = timeline["sources"][clip["source_id"]]
        if Path(clip["source"]).resolve() != Path(source["path"]).resolve():
            raise ValueError("Clip source and source_id disagree.")
        gain = clip.get("source_volume", 1.0)
        if not isinstance(gain, (int, float)) or not math.isfinite(gain) or gain < 0:
            raise ValueError("Clip source_volume must be finite and nonnegative")
        a, b = clip["start"], clip["end"]
        if not all(isinstance(n, (int, float)) and math.isfinite(n) for n in (a, b)) or not 0 <= a < b <= (float("inf") if source.get("kind") in ("photo", "card") else source["duration"] + .001):
            raise ValueError(f"Clip out of source bounds: {clip['id']}")
        if source.get("kind") in ("photo", "card"):
            if a != 0:
                raise ValueError("Photo start must be zero; end is its display duration")
            if clip.get("photo_motion","none") not in ("none","zoom","pan"):
                raise ValueError("Photo motion must be none, zoom or pan")
            if clip.get("photo_background","blur") not in ("blur","pad"):
                raise ValueError("Photo background must be blur or pad")
        if source.get('kind') == 'card':
            for key in ('card_fade_in', 'card_fade_out'):
                value = clip.get(key, 0)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError('Card fades must be finite and nonnegative')
        if clip.get("ambient"):
            ambient = clip["ambient"]
            resource = timeline["sources"][ambient["source_id"]]
            if resource.get("kind","video")!="video" or not resource["audio"]:
                raise ValueError("Photo ambience must refer to a video with audio")
            values = (ambient["start"],ambient["end"],ambient.get("volume",1.))
            if not all(isinstance(v,(float,int)) and math.isfinite(v) for v in values) or not 0<=values[0]<values[1]<=resource["duration"] or values[2]<0:
                raise ValueError("Invalid ambience interval or volume")
        if clip.get("card") is not None:
            validate_card(clip["card"], b - a, settings)
        # Clip list order is authoritative for manual re-editing.
        clip["timeline_start"] = round(position, 4)
        position += b - a
    timeline["duration"] = round(position, 4)
    return timeline


def render_identity(timeline):
    sources = {clip["source_id"] for clip in timeline["clips"]}
    sources.update(c["ambient"]["source_id"] for c in timeline["clips"] if c.get("ambient"))
    identities = {}
    for key in sorted(sources):
        source = timeline["sources"][key]
        current = fingerprint(local_file(source["path"]))
        if current != source["fingerprint"]:
            raise ValueError(f"Source changed since analysis: {source['path']}. Reanalyze first.")
        identities[key] = current
    resources = {}
    for key in ("music", "font", "title_font"):
        if timeline["settings"].get(key):
            resources[key] = fingerprint(local_file(timeline["settings"][key]))
    return digest({"engine": ENGINE_VERSION, "ffmpeg": run(["ffmpeg", "-version"]).splitlines()[0], "timeline": timeline, "sources": identities, "resources": resources})


def validate_video(path, expected_duration, settings):
    meta = probe(path)
    tolerance = max(.15, 2 / settings["fps"])
    failures = []
    if abs(meta["duration"] - expected_duration) > tolerance:
        failures.append(f"Duration {meta['duration']} differs from {expected_duration}")
    if (meta["display_width"], meta["display_height"]) != (settings["width"], settings["height"]):
        failures.append("Output resolution mismatch")
    if not meta["audio"]:
        failures.append("Output lacks normalized audio stream")
    numerator, denominator = map(float, meta["fps"].split("/"))
    if not denominator or abs(numerator / denominator - settings["fps"]) > .02:
        failures.append("Output FPS mismatch")
    if meta["raw_probe"]["streams"][0].get("codec_name") != "h264":
        failures.append("Output is not H.264")
    # Decode both streams completely, catching errors that metadata checks miss.
    run(["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", str(path), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
    result = {"passed": not failures, "failures": failures, "expected_duration": expected_duration,
              "actual_duration": meta["duration"], "resolution": [meta["display_width"], meta["display_height"]],
              "fps": meta["fps"], "audio": meta["audio"], "full_decode": True}
    if failures:
        raise ValueError(f"Video validation failed: {failures}")
    return result
