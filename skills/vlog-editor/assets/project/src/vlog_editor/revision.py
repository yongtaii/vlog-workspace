"""Transactional edits: the agent (Codex or Claude) interprets natural language, this module applies a patch."""
import copy
from datetime import datetime, timezone

from .common import digest, write_json
from .validation import validate_timeline

SETTING_KEYS = {"music_volume", "source_volume", "music", "font", "subtitle_size", "transition",
                "transition_seconds", "color", "width", "height", "fps", "crf", "preset",
                "title_font", "title_font_index"}


def apply_patch(timeline, patch):
    if patch.get("version") != 1 or patch.get("base_digest") != digest(timeline):
        raise ValueError("Patch base_digest does not match the current timeline; rebuild patch")
    changed = copy.deepcopy(timeline)
    operations = patch.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("Patch requires nonempty operations")
    for op in operations:
        action = op["op"]
        if action == "setting":
            if op["key"] not in SETTING_KEYS:
                raise ValueError(f"Unsupported setting: {op['key']}")
            changed["settings"][op["key"]] = op["value"]
            continue
        if action == "insert":
            # A new shot from an already analyzed source, e.g. a dedicated title or ending scene.
            clip = dict(op["clip"])
            source = changed["sources"].get(clip.get("source_id"))
            if source is None:
                raise ValueError(f"Unknown source: {clip.get('source_id')}")
            clip.setdefault("phase", "explore")
            clip.update(source=source["path"], kind=source.get("kind", "video"))
            ids = [c["id"] for c in changed["clips"]]
            before = op.get("before_id")
            if before is not None and before not in ids:
                raise ValueError(f"Unknown before_id: {before}")
            changed["clips"].insert(ids.index(before) if before is not None else len(ids), clip)
            continue
        clip = next((c for c in changed["clips"] if c["id"] == op["clip_id"]), None)
        if clip is None:
            raise ValueError(f"Unknown clip: {op['clip_id']}")
        if action == "trim":
            clip["start"], clip["end"] = op["start"], op["end"]
        elif action in ("photo_duration","photo_style","ambience"):
            if changed['sources'][clip['source_id']].get('kind')!='photo':
                raise ValueError("Photo edits require a photo clip")
            if action=='photo_duration':
                clip['end']=op['seconds']
            elif action=='photo_style':
                clip['photo_motion']=op.get('motion',clip.get('photo_motion','none'))
                clip['photo_background']=op.get('background',clip.get('photo_background','blur'))
            elif op.get('value') is None:
                clip.pop('ambient',None)
            else:
                clip['ambient']=op['value']
        elif action == "caption":
            if not isinstance(op["text"], str):
                raise ValueError("Caption must be text")
            clip["caption"] = op["text"]
        elif action == "card":
            if op.get("value") is None:
                clip.pop("card", None)
            else:
                clip["card"] = op["value"]
        elif action == "audio_gain":
            clip["source_volume"] = op["value"]
        elif action == "remove":
            changed["clips"].remove(clip)
        elif action == "move_before":
            before = op.get("before_id")
            if before == clip["id"]:
                continue
            changed["clips"].remove(clip)
            if before is None:
                changed["clips"].append(clip)
            else:
                ids = [c["id"] for c in changed["clips"]]
                if before not in ids:
                    raise ValueError(f"Unknown before_id: {before}")
                changed["clips"].insert(ids.index(before), clip)
        else:
            raise ValueError(f"Unsupported operation: {action}")
    validate_timeline(changed)
    return changed


def revise(timeline, patch, request, history_dir):
    changed = apply_patch(timeline, patch)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    identity = f'{stamp}-{digest(changed)[:10]}'
    write_json(history_dir / f'{identity}.json', {
        'request': request, 'patch': patch, 'before': timeline, 'after_digest': digest(changed)})
    return changed
