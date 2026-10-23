from __future__ import annotations

import math
from statistics import median

from .story import PHASES



def distance(a, b):
    return (int(a, 16) ^ int(b, 16)).bit_count()


def build_candidates(analysis, config, hints=None):
    hints = hints or {}
    candidates, rejected = [], []
    videos = sorted(analysis["videos"], key=lambda v: (v.get("creation_time") or "9999", v["relative_path"]))
    for video_index, video in enumerate(videos):
        hint = hints.get(video["relative_path"], {})
        phase = hint.get("phase", "explore")
        if phase not in PHASES:
            raise ValueError(f"Unknown story phase: {phase}")
        for scene_index, scene in enumerate(video["scenes"]):
            start = scene["start"]
            while start < scene["end"] - .001:
                end = min(start + config["clip_seconds"], scene["end"])
                samples = [s for s in video["samples"] if start <= s["time"] < end]
                if not samples:
                    samples = [min(video["samples"], key=lambda s: abs(s["time"] - (start + end) / 2))]
                reasons = []
                if end - start < 1.0:
                    reasons.append("too_short")
                if hint.get("exclude"):
                    reasons.append("manual_exclusion")
                if any(start < r[1] and end > r[0] for r in hint.get("exclude_ranges", [])):
                    reasons.append("manual_exclusion_range")
                if sum(s["sharpness"] < config["min_sharpness"] for s in samples) / len(samples) >= .5:
                    reasons.append("blur")
                if sum(s["shake"] > config["max_shake"] and s["tracked"] >= 8 for s in samples) / len(samples) >= .5:
                    reasons.append("shake")
                if median(s["exposure"] for s in samples) < .035 or median(s["exposure"] for s in samples) > .97:
                    reasons.append("extreme_exposure")
                sharpness = median(s["sharpness"] for s in samples)
                motion = median(s["motion"] for s in samples)
                # Quality saturates; scene diversity, priority and coverage drive later choices.
                quality = min(1., math.log1p(sharpness) / 8.) * .35
                quality += (1 - abs(median(s["exposure"] for s in samples) - .5) * 2) * .2
                quality += min(motion / .02, 1.) * .1
                quality -= min(median(s["shake"] for s in samples) / config["max_shake"], 1.) * .15
                candidate = {"id": f'{video["id"]}-{scene_index}-{start:.3f}', "source": video["path"],
                             "source_id": video["id"], "source_order": video_index, "scene": scene_index, "kind": "video",
                             "capture_time": hint.get("capture_time",video.get("creation_time")),
                             "location": hint.get("location"), "event": hint.get("event"),
                             "start": round(start, 4), "end": round(end, 4), "phase": phase,
                             "tags": hint.get("tags", []), "caption": hint.get("caption", ""),
                             "priority": float(hint.get("priority", 0)), "quality": round(quality, 4),
                             "hashes": [s["hash"] for s in samples],
                             "reason": ["quality_eligible", "chronological_context", "diversity_selection"],
                             "metrics": {"sharpness": sharpness, "motion": motion,
                                         "shake": median(s["shake"] for s in samples)}}
                if reasons:
                    rejected.append({**candidate, "reason": reasons})
                else:
                    candidates.append(candidate)
                start = end
    return candidates, rejected, videos


def select_clips(candidates, rejected, config):
    selected, total, source_counts, scene_counts, phase_counts = [], 0., {}, {}, {}
    budget = float("inf") if config["target_seconds"] is None else config["target_seconds"]
    while candidates and total < budget - .01:
        def utility(c):
            return (c["quality"] + c["priority"] + .4 / (1 + source_counts.get(c["source_id"], 0))
                    + .3 / (1 + scene_counts.get((c["source_id"], c["scene"]), 0))
                    + .2 / (1 + phase_counts.get(c["phase"], 0)))
        candidate = max(candidates, key=utility)
        candidates.remove(candidate)
        # Require a majority of sampled hashes to match a previous scene, not a single similar frame.
        duplicate = any(sum(any(distance(h, old) <= config["duplicate_distance"] for old in chosen["hashes"])
                            for h in candidate["hashes"]) / len(candidate["hashes"]) >= .75 for chosen in selected)
        if duplicate:
            rejected.append({**candidate, "reason": ["perceptual_duplicate"]})
            continue
        duration = min(candidate["end"] - candidate["start"], budget - total)
        if duration < 1:
            rejected.append({**candidate, "reason": ["remaining_budget_under_one_second"]})
            break
        candidate["end"] = round(candidate["start"] + duration, 4)
        selected.append(candidate)
        total += duration
        for counts, key in ((source_counts, candidate["source_id"]),
                            (scene_counts, (candidate["source_id"], candidate["scene"])),
                            (phase_counts, candidate["phase"])):
            counts[key] = counts.get(key, 0) + 1
    rejected.extend({**c, "reason": ["duration_budget"]} for c in candidates)
    if not selected:
        raise ValueError("No eligible clips. Review analysis/contact sheets and thresholds or hints.")
    return selected, rejected
