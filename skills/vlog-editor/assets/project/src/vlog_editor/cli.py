from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from .analyze import analyze
from .bookends import add_bookends
from .common import validate_target, digest, local_file, protect_output, read_json, require_tools, write_json
from .planner import make_timeline
from .render import render, validate_timeline
from .revision import revise
from .storyboard import write_storyboard


def load_config(path):
    config = read_json(path)
    validate_target(config.get("target_seconds"))
    for key in ("sample_interval", "clip_seconds", "max_shake", "scene_threshold", "fps", "width", "height"):
        value = config.get(key)
        if not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key} must be a finite positive number")
    if config["clip_seconds"] < 1:
        raise ValueError("clip_seconds must be at least 1")
    if not 0 <= config["duplicate_distance"] <= 64:
        raise ValueError("duplicate_distance must be in [0,64]")
    for key in ("music", "font", "title_font"):
        if config.get(key):
            config[key] = str(local_file(Path(path).parent / config[key]))
    if config.get('bookends', {}).get('font'):
        config['bookends']['font'] = str(local_file(Path(path).parent / config['bookends']['font']))
    return config


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local travel vlog editor; no original file is modified")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root (default: current directory)")
    parser.add_argument("--lane", help="Separate agent workspace: analysis/lanes/<lane>, preview/<lane>, output/<lane>")
    parser.add_argument("--title-style", choices=("bookends", "cards"), default="bookends",
                        help="New plans: separate dated bookend cards, or hints @title/@ending overlaid on real shots")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("doctor", help="Check dependencies and encoders")
    board = subs.add_parser("storyboard", help="Write offline HTML storyboard")
    board.add_argument("--timeline", type=Path, default=None)
    edit = subs.add_parser("revise", help="Apply agent-generated (Codex/Claude) patch without replanning")
    edit.add_argument("--timeline", type=Path, default=None)
    edit.add_argument("--patch", type=Path, required=True)
    edit.add_argument("--request", required=True, help="Original natural-language request for history")
    edit.add_argument("--render", action="store_true", help="Preview, validate, then incrementally render")
    inspect = subs.add_parser("inspect", help="Print timeline digest and IDs to construct a revision patch")
    inspect.add_argument("--timeline", type=Path, default=None)
    titles = subs.add_parser("bookends", help="Add/update dated opening and ending without replanning body shots")
    titles.add_argument("--timeline", type=Path, default=None)
    titles.add_argument("--title")
    titles.add_argument("--ending")
    titles.add_argument("--date", dest="date_text")
    titles.add_argument("--font")
    titles.add_argument("--opening-seconds", type=float)
    titles.add_argument("--closing-seconds", type=float)
    titles.add_argument("--enabled", action=argparse.BooleanOptionalAction, default=None)
    for name in ("analyze", "plan", "preview", "render", "run"):
        cmd = subs.add_parser(name)
        cmd.add_argument("--config", type=Path, default=None)
        cmd.add_argument("--timeline", type=Path, default=None)
        if name in ("plan", "run"):
            cmd.add_argument("--hints", type=Path, help="Optional per-video story hints JSON")
    args = parser.parse_args(argv)
    root = args.project.expanduser().resolve()
    def resolve(path):
        return path if path.is_absolute() else root / path
    # A lane keeps one agent's timeline, history and renders apart from the default (Codex) workspace.
    # Source analysis and the checksum-verified cache stay shared.
    if args.lane and not args.lane.replace("-", "").replace("_", "").isalnum():
        print("Error: --lane must be letters, digits, - or _", file=sys.stderr)
        return 1
    work = root / "analysis/lanes" / args.lane if args.lane else root / "analysis"
    preview_dir = root / "preview" / args.lane if args.lane else root / "preview"
    output_dir = root / "output" / args.lane if args.lane else root / "output"
    storyboard_path, history_dir = work / "storyboard.html", work / "revisions"
    if getattr(args, "timeline", False) is None:
        args.timeline = work / "timeline.json"
    if getattr(args, "config", False) is None:
        lane_config = root / f"config.{args.lane}.json" if args.lane else None
        args.config = lane_config if lane_config and lane_config.is_file() else Path("config.json")
    try:
        require_tools()
        if args.command == "doctor":
            from .common import run
            import cv2
            print(run(["ffmpeg", "-version"]).splitlines()[0])
            encoders = run(["ffmpeg", "-v", "error", "-encoders"])
            filters = run(["ffmpeg", "-v", "error", "-filters"])
            if "libx264" not in encoders or "aac" not in encoders:
                raise ValueError("FFmpeg requires libx264 and AAC encoders")
            print(f"OpenCV {cv2.__version__}; H.264/AAC ready; PNG subtitle overlay available: {'overlay' in filters}")
            return 0
        timeline_path = resolve(args.timeline)
        protect_output(timeline_path, root / "input")
        if args.command == "bookends":
            original = read_json(timeline_path)
            overrides = {key: getattr(args, key) for key in ('title','ending','date_text','font','opening_seconds','closing_seconds','enabled') if getattr(args,key) is not None}
            if overrides.get('font'):
                overrides['font'] = str(local_file(resolve(Path(overrides['font']))))
            timeline = validate_timeline(add_bookends(original, read_json(root / 'analysis/analysis.json'), root / 'analysis', overrides))
            protect_output(timeline_path, root / 'input', [v['path'] for v in original['sources'].values()])
            from datetime import datetime, timezone
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            write_json(history_dir / f'{stamp}-bookends.json', {'request': 'Add/update dated opening and ending', 'before': original, 'after_digest': digest(timeline)})
            write_json(timeline_path, timeline)
            write_storyboard(read_json(root / 'analysis/analysis.json'), timeline, storyboard_path)
            print(f"Opening/ending updated: {timeline['duration']:.2f}s; render preview next")
            return 0
        if args.command == "inspect":
            timeline = read_json(timeline_path)
            print(json.dumps({"base_digest": digest(timeline), "clips": timeline["clips"], "settings": timeline["settings"]}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "revise":
            timeline = read_json(timeline_path)
            protect_output(timeline_path, root / "input", [v["path"] for v in timeline["sources"].values()])
            history = protect_output(history_dir, timeline["input_dir"])
            timeline = revise(timeline, read_json(resolve(args.patch)), args.request, history)
            write_json(timeline_path, timeline)
            write_storyboard(read_json(root / "analysis/analysis.json"), timeline, storyboard_path)
            if args.render:
                render(timeline, output_dir, preview=True, cache_dir=root / "analysis/cache", preview_dir=preview_dir)
                render(timeline, output_dir, cache_dir=root / "analysis/cache", preview_dir=preview_dir)
            print(f"Revision applied; storyboard: {storyboard_path}")
            return 0
        if args.command == "storyboard":
            analysis = read_json(root / "analysis/analysis.json")
            timeline = read_json(timeline_path) if timeline_path.exists() else None
            print(write_storyboard(analysis, timeline, storyboard_path))
            return 0
        if args.command in ("analyze", "plan", "run"):
            config = load_config(resolve(args.config))
        if args.command in ("analyze", "run"):
            analysis = analyze(root / "input", root / "analysis", config)
            write_storyboard(analysis, None, storyboard_path)
            print(f"Analysis: {root / 'analysis/analysis.json'} ({len(analysis['errors'])} input errors)")
        if args.command in ("plan", "run"):
            if args.command == "plan":
                analysis = read_json(root / "analysis/analysis.json")
            hints = read_json(resolve(args.hints)) if args.hints else {}
            if args.title_style == "cards":
                # @title/@ending become clip.card overlays on the first/last planned shots.
                timeline = validate_timeline(make_timeline(analysis, config, hints))
            else:
                card_overrides = {}
                for key, title_key, duration_key in (('@title','title','opening_seconds'),('@ending','ending','closing_seconds')):
                    if hints.get(key):
                        if hints[key].get('title'):
                            card_overrides[title_key] = hints[key]['title']
                        if hints[key].get('seconds'):
                            card_overrides[duration_key] = hints[key]['seconds']
                # Bookends own the title here; keep make_timeline from also overlaying cards.
                body_hints = {k: v for k, v in hints.items() if k not in ('@title', '@ending')}
                timeline = validate_timeline(add_bookends(make_timeline(analysis, config, body_hints), analysis, root / "analysis", card_overrides))
            protect_output(timeline_path, root / "input", [v["path"] for v in analysis["videos"]+analysis.get("photos",[])])
            write_json(timeline_path, timeline)
            write_storyboard(analysis, timeline, storyboard_path)
            print(f"Timeline: {timeline_path}, {timeline['duration']:.2f}s, {len(timeline['clips'])} clips")
            for warning in timeline["warnings"]:
                print(f"Note: {warning}")
        if args.command in ("preview", "render", "run"):
            timeline = read_json(timeline_path)
            # Dedicated preview/render commands preserve all manual timeline edits.
            if args.command in ("preview", "run"):
                print(f"Validated preview: {render(timeline, output_dir, preview=True, cache_dir=root / 'analysis/cache', preview_dir=preview_dir)}")
            if args.command in ("render", "run"):
                print(f"Validated full render: {render(timeline, output_dir, preview=False, cache_dir=root / 'analysis/cache', preview_dir=preview_dir)}")
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
