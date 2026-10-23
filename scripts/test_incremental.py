#!/usr/bin/env python3
"""Behavioral regression for actual revision CLI and FFmpeg cache reuse on smoke fixtures."""
import argparse
from pathlib import Path

from vlog_editor.cli import main
from vlog_editor.common import digest, fingerprint, read_json, write_json


def test():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True, help='Synthetic project from smoke_test.py')
    args = parser.parse_args()
    root = args.project.resolve()
    analysis = read_json(root / 'analysis/analysis.json')
    if any('synthetic' not in c.get('tags',[]) for c in read_json(root/'analysis/timeline.json')['clips']):
        raise SystemExit('This regression script only accepts synthetic-tagged fixtures')
    before = {v['path']: fingerprint(v['path']) for v in analysis['videos']}
    summaries = []
    def both():
        assert main(['--project',str(root),'preview']) == 0
        assert main(['--project',str(root),'render']) == 0
        return events()
    def events():
        return read_json(root/'preview/preview-validation.json')['cache'] + read_json(root/'output/full-validation.json')['cache']
    def misses(event_list, kind):
        return sum(e['kind']==kind and e['status']=='rendered' for e in event_list)
    def edit(operations, request):
        timeline = read_json(root/'analysis/timeline.json')
        patch = {'version':1,'base_digest':digest(timeline),'operations':operations}
        write_json(root/'analysis/patch.json',patch)
        assert main(['--project',str(root),'revise','--patch','analysis/patch.json','--request',request,'--render']) == 0
        results = events()
        summaries.append({'request':request,'misses':{k:misses(results,k) for k in ('video','audio','mix')}})
        return results
    assert misses(both(),'video') == 0
    timeline = read_json(root/'analysis/timeline.json')
    clip_id = timeline['clips'][1]['id']
    results = edit([{'op':'caption','clip_id':clip_id,'text':timeline['clips'][1].get('caption','')+' 수정'}], '두 번째 컷의 자막만 바꿔줘')
    assert misses(results,'video') == 1 and misses(results,'audio') == 0 and misses(results,'mix') == 0
    results = edit([{'op':'setting','key':'music_volume','value':timeline['settings']['music_volume']*.5}], '음악 볼륨을 절반으로 낮춰줘')
    assert misses(results,'video') == 0 and misses(results,'audio') == 0 and misses(results,'mix') == 2
    results = edit([{'op':'audio_gain','clip_id':clip_id,'value':timeline['clips'][1].get('source_volume',1.)*.5}], '두 번째 컷의 현장음만 절반으로 줄여줘')
    assert misses(results,'video') == 0 and misses(results,'audio') == 1 and misses(results,'mix') == 2
    timeline = read_json(root/'analysis/timeline.json')
    second = timeline['clips'][1]
    results = edit([{'op':'trim','clip_id':clip_id,'start':second['start'],'end':second['end']-1}],
                   '두 번째 컷의 끝을 1초 줄여줘')
    # One edited shot, plus a different partial shot at the preview boundary.
    assert misses(results,'video') == 2 and misses(results,'audio') == 2
    timeline = read_json(root/'analysis/timeline.json')
    results = edit([{'op':'move_before','clip_id':timeline['clips'][-1]['id'],'before_id':timeline['clips'][0]['id']}],
                   '마지막 장면을 맨 앞으로 옮겨줘')
    # Whole shots survive reorder; only the newly clipped preview boundary may be new.
    assert misses(results,'video') <= 1 and misses(results,'audio') <= 1
    # Same request on an obsolete timeline must not change the current edit.
    timeline = read_json(root/'analysis/timeline.json')
    assert main(['--project',str(root),'revise','--patch','analysis/patch.json','--request','stale patch']) == 1
    assert read_json(root/'analysis/timeline.json') == timeline
    assert before == {p:fingerprint(p) for p in before}
    assert (root/'analysis/storyboard.html').is_file()
    write_json(root/'output/incremental-validation.json',{'passed':True,'source_hashes_unchanged':True,'cases':summaries})
    print('Incremental regression passed:', summaries)


if __name__ == '__main__':
    test()
