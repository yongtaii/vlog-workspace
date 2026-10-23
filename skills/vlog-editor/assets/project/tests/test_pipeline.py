import json

import pytest

from vlog_editor.cli import load_config
from vlog_editor.common import ROOT, fingerprint, protect_output
from vlog_editor.planner import make_timeline
from vlog_editor.render import render, validate_timeline


@pytest.fixture
def config():
    return json.loads((ROOT / "config.json").read_text())


def video(key, sharpness=200, shake=0, hash_value="0000000000000000"):
    return {"id": key, "path": f"/fixture/{key}.mp4", "relative_path": f"{key}.mp4", "duration": 6,
            "video_stream": 0, "audio": [], "fingerprint": {},
            "scenes": [{"start": 0, "end": 6}], "samples": [
                {"time": t, "sharpness": sharpness, "shake": shake, "tracked": 40, "motion": .005,
                 "exposure": .5, "hash": hash_value} for t in (0, 2, 4)]}


def analysis(videos):
    return {"input_dir": "/fixture", "videos": videos}


def test_reject_blur_shake_duplicate_and_cap_duration(config):
    config.update(clip_seconds=6, target_seconds=18)
    timeline = make_timeline(analysis([video("a"), video("b"), video("blur", sharpness=1),
                                       video("shake", shake=.2), video("different", hash_value="ffffffffffffffff")]), config)
    assert len(timeline["clips"]) == 2
    reasons = [r for clip in timeline["rejected"] for r in clip["reason"]]
    assert {"blur", "shake", "perceptual_duplicate"} <= set(reasons)
    assert timeline["duration"] == 12
    assert all(c["end"] - c["start"] <= 6 for c in timeline["clips"])


def test_story_tags_override_filename_order(config):
    config.update(clip_seconds=6, target_seconds=12)
    timeline = make_timeline(analysis([video("a", hash_value="ffffffffffffffff"), video("z")]), config,
                             {"a.mp4": {"phase": "closing"}, "z.mp4": {"phase": "opening", "caption": "여행 시작"}})
    assert [c["phase"] for c in timeline["clips"]] == ["opening", "closing"]
    assert timeline["clips"][0]["caption"] == "여행 시작"


def test_manual_order_recomputes_timing_and_rejects_invalid_bounds(config):
    config.update(clip_seconds=6, target_seconds=12)
    timeline = make_timeline(analysis([video("a"), video("b", hash_value="ffffffffffffffff")]), config)
    timeline["clips"].reverse()
    timeline["clips"][0]["end"] = 2
    validate_timeline(timeline)
    assert timeline["duration"] == 8
    assert timeline["clips"][1]["timeline_start"] == 2
    timeline["clips"][0]["end"] = 7
    with pytest.raises(ValueError, match="bounds"):
        validate_timeline(timeline)


def test_source_write_and_symlink_alias_are_forbidden(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="input"):
        protect_output(alias / "output.mp4", source)
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"original")
    with pytest.raises(ValueError, match="source"):
        protect_output(clip, source, [clip])
    assert clip.read_bytes() == b"original"


def test_full_render_requires_preview_without_touching_source(config, tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    file = source / "a.mp4"
    file.write_bytes(b"original data, not decoded before gate")
    item = video("a")
    item.update(path=str(file), fingerprint=fingerprint(file))
    config["clip_seconds"] = 6
    timeline = make_timeline({"input_dir": str(source), "videos": [item]}, config)
    before = file.read_bytes()
    with pytest.raises(ValueError, match="preview"):
        render(timeline, tmp_path / "output", preview=False)
    assert file.read_bytes() == before


def test_zero_sample_interval_rejected(config, tmp_path):
    config["sample_interval"] = 0
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="sample_interval"):
        load_config(path)


def test_manual_exclusion_range(config):
    config["clip_seconds"] = 3
    timeline = make_timeline(analysis([video("a")]), config,
                             {"a.mp4": {"exclude_ranges": [[0, 2]]}})
    assert all(c["start"] >= 3 for c in timeline["clips"])
    assert any("manual_exclusion_range" in c["reason"] for c in timeline["rejected"])


def test_modified_original_rejected_before_render(config, tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    file = source / "a.mp4"
    file.write_bytes(b"first")
    item = video("a")
    item.update(path=str(file), fingerprint=fingerprint(file))
    config["clip_seconds"] = 6
    timeline = make_timeline({"input_dir": str(source), "videos": [item]}, config)
    file.write_bytes(b"different")
    with pytest.raises(ValueError, match="Source changed"):
        render(timeline, tmp_path / "output", preview=True)
    assert file.read_bytes() == b"different"


def test_unlimited_duration_exceeds_old_ninety_second_default(config):
    config.update(target_seconds=None,clip_seconds=6,duplicate_distance=0)
    videos=[video(f'v{i:02}',hash_value=f'{i:016x}') for i in range(20)]
    timeline=make_timeline(analysis(videos),config)
    assert timeline['duration']==120
    assert len(timeline['clips'])==20
    assert timeline['settings']['target_seconds'] is None
    validate_timeline(timeline)
    json.dumps(timeline,allow_nan=False)
