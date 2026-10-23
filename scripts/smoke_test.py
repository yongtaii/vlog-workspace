#!/usr/bin/env python3
"""Generate synthetic media in analysis/smoke; never mixes it with real input/."""
import argparse
import json
from pathlib import Path

from vlog_editor.common import ROOT, fingerprint, run, write_json
from vlog_editor.cli import main


def smoke():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=ROOT / "analysis/smoke")
    args = parser.parse_args()
    root = args.directory.resolve()
    # A dedicated disposable fixture folder; refuse to reuse files.
    if root.exists():
        raise SystemExit(f"Smoke directory already exists; choose another --directory: {root}")
    (root / "input/videos").mkdir(parents=True)
    config = json.loads((ROOT / "config.json").read_text())
    config.update(width=640, height=360, fps=24, preset="ultrafast", target_seconds=36,
                  clip_seconds=6, sample_interval=2, min_sharpness=10, duplicate_distance=0,
                  scene_threshold=.9, max_shake=.15, transition="fade")
    config["color"]["enabled"] = True
    write_json(root / "config.json", config)
    fonts = [Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
             Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    font = next((p for p in fonts if p.is_file()), None)
    if not font:
        raise SystemExit("Smoke subtitles require a local font; update fonts list in scripts/smoke_test.py")
    config["font"] = str(font)
    config["subtitle_size"] = 28
    config['bookends'] = {'enabled': False}
    hints = {}
    for i, phase in enumerate(("opening", "journey", "explore", "explore", "highlight", "closing")):
        path = root / "input/videos" / f"{i:02}-{phase}.mp4"
        source = f"testsrc2=size={'240x426' if i == 2 else '640x360'}:rate=24:duration=6"
        vf = f"hue=h={i * 47},drawbox=x={20+i*43}:y={30+i*17}:w={50+i*21}:h=90:color=white:t=fill"
        command = ["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "lavfi", "-i", source]
        if i % 2 == 0:
            command += ["-f", "lavfi", "-i", f"sine=frequency={330+i*100}:sample_rate=48000:duration=6"]
        command += ["-vf", vf, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
        if i % 2 == 0:
            command += ["-c:a", "aac"]
        command += ["-t", "6", str(path)]
        run(command)
        hints["videos/"+path.name] = {"phase": phase, "tags": ["synthetic"], "caption": f"여행 테스트 {i + 1}" if "Apple" in font.name else f"Travel test {i + 1}"}
    # Test optional BGM using a generated local WAV.
    music = root / "music.wav"
    run(["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "lavfi", "-i", "sine=frequency=220:duration=4", str(music)])
    config["music"] = "music.wav"
    write_json(root / "config.json", config)
    write_json(root / "hints.json", hints)
    before = {str(p): fingerprint(p) for p in (root / "input/videos").glob("*")}
    status = main(["--project", str(root), "run", "--hints", "hints.json"])
    if status:
        raise SystemExit(status)
    assert before == {p: fingerprint(p) for p in before}, "Source files changed!"
    preview = json.loads((root / "preview/preview-validation.json").read_text())
    full = json.loads((root / "output/full-validation.json").read_text())
    assert abs(preview["actual_duration"] - 30) < .15
    assert abs(full["actual_duration"] - 36) < .15
    # An edited timeline must invalidate the preview gate.
    timeline = json.loads((root / "analysis/timeline.json").read_text())
    timeline["settings"]["source_volume"] = .5
    write_json(root / "analysis/timeline.json", timeline)
    assert main(["--project", str(root), "render"]) == 1, "Stale preview gate was accepted"
    timeline["settings"]["source_volume"] = config["source_volume"]
    write_json(root / "analysis/timeline.json", timeline)
    print(f"Smoke test passed: 30s preview, 36s full, mixed audio/portrait/BGM/fade/color/subtitles, source hashes unchanged, stale preview rejected. {root}")


if __name__ == "__main__":
    smoke()
