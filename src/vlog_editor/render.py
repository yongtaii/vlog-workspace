"""Incremental render orchestration: cached video/audio shots, assemblies, mix, mux."""
from pathlib import Path
import tempfile

from .cache import Cache
from .common import fingerprint, local_file, protect_output, read_json, run, write_json
from .cut import render_shot, video_key
from .sound import audio_key, mix_audio, render_audio
from .validation import render_identity, validate_timeline, validate_video


def concat(paths, durations, destination, video):
    listing = destination.parent / "concat.txt"
    def quote(path):
        return str(path).replace("'", "'\\''")
    listing.write_text("".join(f"file '{quote(p)}'\nduration {d:.9f}\n" for p, d in zip(paths, durations)), encoding="utf-8")
    args = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", str(listing)]
    args += ["-an", "-c:v", "copy", "-movflags", "+faststart"] if video else ["-vn", "-c:a", "pcm_s16le"]
    run(args + [str(destination)])


def render(timeline, output_dir, preview=False, cache_dir=None, preview_dir=None):
    timeline = validate_timeline(timeline)
    settings = timeline["settings"]
    identity = render_identity(timeline)
    output_dir = protect_output(output_dir, timeline["input_dir"])
    cache_dir = protect_output(cache_dir or output_dir.parent / "analysis/cache", timeline["input_dir"])
    preview_dir = protect_output(preview_dir or output_dir, timeline["input_dir"])
    originals = [Path(s["path"]).resolve() for s in timeline["sources"].values()]
    resources = {k: fingerprint(local_file(settings[k])) for k in ("music", "font", "title_font") if settings.get(k)}
    originals.extend(Path(p["path"]) for p in resources.values())
    for directory in (output_dir, preview_dir, cache_dir):
        if any(directory == p or directory in p.parents for p in originals):
            raise ValueError("Generated directories must not contain originals, music or fonts")
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    receipt_path, preview_path = preview_dir / "preview-validation.json", preview_dir / "preview.mp4"
    if not preview:
        if not receipt_path.is_file() or not preview_path.is_file():
            raise ValueError("Render and validate a preview before the full render.")
        receipt = read_json(receipt_path)
        if not receipt.get("passed") or receipt.get("render_identity") != identity or receipt.get("preview_fingerprint") != fingerprint(preview_path):
            raise ValueError("Preview gate is stale or failed. Render the preview again after editing the timeline/assets.")
    limit = min(30., timeline["duration"]) if preview else timeline["duration"]
    destination = protect_output((preview_dir / "preview.mp4" if preview else output_dir / "vlog.mp4"), timeline["input_dir"], originals)
    cache = Cache(cache_dir, run(["ffmpeg", "-version"]).splitlines()[0])
    videos, audios, durations, elapsed = [], [], [], 0.
    for clip in timeline["clips"]:
        raw_duration = min(clip["end"] - clip["start"], limit - elapsed)
        if raw_duration <= .001:
            break
        frames = round((elapsed + raw_duration) * settings["fps"]) - round(elapsed * settings["fps"])
        if frames < 1:
            raise ValueError("Clip is shorter than one output frame")
        duration = frames / settings["fps"]
        source = timeline["sources"][clip["source_id"]]
        ambient_source = timeline["sources"][clip["ambient"]["source_id"]] if clip.get("ambient") else None
        videos.append(cache.get("video", video_key(clip, source, settings, duration, resources.get("font"), resources.get("title_font") or resources.get("font")), ".mp4",
                                lambda path: render_shot(clip, source, settings, duration, path)))
        audios.append(cache.get("audio", audio_key(clip, source, settings, duration, ambient_source), ".wav",
                                lambda path: render_audio(clip, source, settings, duration, path, ambient_source)))
        durations.append(duration)
        elapsed += raw_duration
    joined_video = cache.get("video-assembly", {"paths": [p.name for p in videos], "durations": durations}, ".mp4",
                             lambda path: concat(videos, durations, path, video=True))
    joined_audio = cache.get("audio-assembly", {"paths": [p.name for p in audios], "durations": durations}, ".wav",
                             lambda path: concat(audios, durations, path, video=False))
    mixed_audio = cache.get("mix", {"assembly": joined_audio.name, "duration": limit,
                                   "music": resources.get("music"), "music_volume": settings["music_volume"],
                                   "source_volume": settings["source_volume"]}, ".m4a",
                            lambda path: mix_audio(joined_audio, settings, limit, path))
    with tempfile.TemporaryDirectory(prefix="vlog-mux-", dir=destination.parent) as temporary:
        final = Path(temporary) / "final.mp4"
        run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(joined_video), "-i", str(mixed_audio),
             "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-t", str(limit), "-movflags", "+faststart", str(final)])
        validation = validate_video(final, limit, settings)
        final.replace(destination)
    validation.update({"render_identity": identity, "preview_fingerprint" if preview else "output_fingerprint": fingerprint(destination),
                       "kind": "preview" if preview else "full", "visual_review": "pending_human_review",
                       "cache": cache.events})
    write_json(receipt_path if preview else output_dir / "full-validation.json", validation)
    counts = {kind: sum(e["kind"] == kind and e["status"] == "rendered" for e in cache.events)
              for kind in ("video", "audio", "mix")}
    print(f"Rendered cache misses: {counts}; reused {sum(e['status']=='reused' for e in cache.events)} artifacts", flush=True)
    return destination
