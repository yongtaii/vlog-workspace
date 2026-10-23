import json

from vlog_editor.cli import main
from vlog_editor.common import digest, write_json


def test_lane_reads_its_own_timeline_and_rejects_unsafe_names(tmp_path, capsys):
    write_json(tmp_path/'analysis/timeline.json', {'lane': 'default'})
    write_json(tmp_path/'analysis/lanes/claude/timeline.json', {'lane': 'claude', 'clips': [], 'settings': {}})
    assert main(['--project', str(tmp_path), '--lane', 'claude', 'inspect']) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed['base_digest'] == digest({'lane': 'claude', 'clips': [], 'settings': {}})
    assert main(['--project', str(tmp_path), '--lane', '../escape', 'inspect']) == 1
    assert json.loads((tmp_path/'analysis/timeline.json').read_text()) == {'lane': 'default'}
