import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from vlog_editor.bookends import add_bookends, capture_date, find_font
from vlog_editor.common import ROOT, fingerprint
from vlog_editor.cut import video_key
from vlog_editor.sound import audio_key
from vlog_editor.storyboard import write_storyboard
from vlog_editor.validation import validate_timeline


def test_date_uses_capture_timezone_and_preserves_unknown():
    assert capture_date([{'capture_time':'2026-10-03T23:30:00Z'}])=='2026.10.04'
    assert capture_date([{'capture_time':'2026-10-03T12:00:00+09:00'},
                         {'capture_time':'2026-10-04T01:00:00+09:00'}])=='2026.10.03 — 2026.10.04'
    assert capture_date([{}])=='날짜 미상'


def fixture(tmp_path):
    root=tmp_path
    (root/'input').mkdir()
    picture=root/'input/original.png'
    Image.new('RGB',(640,360),'navy').save(picture)
    config=json.loads((ROOT/'config.json').read_text())
    config.update(width=640,height=360)
    source={'kind':'photo','path':str(picture),'duration':3.,'audio':[],'video_stream':0,'fingerprint':fingerprint(picture)}
    clip={'id':'body','kind':'photo','source_id':'p','source':str(picture),'start':0.,'end':3.,
          'phase':'explore','capture_time':'2026-10-04T14:00:00+09:00','caption':''}
    return {'version':1,'input_dir':str(root/'input'),'sources':{'p':source},'settings':config,'clips':[clip]}, {'input_dir':str(root/'input'),'videos':[],'photos':[{
        'id':'p','path':str(picture),'relative_path':'original.png','duration':3.,'orientation':'landscape','audio':[],
        'samples':[{'time':0.,'frame':str(picture)}],'contact_sheets':[str(picture)]}]}


def test_add_update_and_disable_keep_body_and_original_intact(tmp_path):
    timeline,analysis=fixture(tmp_path)
    before=copy.deepcopy(timeline)
    result=add_bookends(timeline,analysis,tmp_path/'analysis')
    validate_timeline(result)
    assert [c['kind'] for c in result['clips']]==['card','photo','card']
    assert result['duration']==11.
    assert result['clips'][0]['date_text']=='2026.10.04'
    assert result['clips'][1]['start']==before['clips'][0]['start']
    assert timeline==before
    assert fingerprint(before['sources']['p']['path'])==before['sources']['p']['fingerprint']
    closing=result['sources']['generated-bookend-closing']['fingerprint']
    revised=add_bookends(result,analysis,tmp_path/'analysis',{'title':'새로운 하루'})
    assert len(revised['clips'])==3
    assert revised['sources']['generated-bookend-closing']['fingerprint']==closing
    assert revised['sources']['generated-bookend-opening']['fingerprint']!=result['sources']['generated-bookend-opening']['fingerprint']
    disabled=add_bookends(revised,analysis,tmp_path/'analysis',{'enabled':False})
    assert disabled['clips'][0]['id']=='body' and len(disabled['clips'])==1
    assert disabled['duration']==3.
    output=write_storyboard(analysis,result,tmp_path/'analysis/storyboard.html')
    assert '2026.10.04' in output.read_text()


def test_bookends_do_not_invalidate_body_cache_keys(tmp_path):
    timeline,analysis=fixture(tmp_path)
    clip=timeline['clips'][0];source=timeline['sources']['p'];settings=timeline['settings']
    video=video_key(clip,source,settings,3.,None)
    audio=audio_key(clip,source,settings,3.)
    result=add_bookends(timeline,analysis,tmp_path/'analysis')
    assert video_key(result['clips'][1],result['sources']['p'],result['settings'],3.,None)==video
    assert audio_key(result['clips'][1],result['sources']['p'],result['settings'],3.)==audio


def test_cache_keys_are_distinct_for_different_sources_and_card_fades(tmp_path):
    timeline,analysis=fixture(tmp_path)
    clip=timeline['clips'][0];source=timeline['sources']['p'];settings=timeline['settings']
    original_video=video_key(clip,source,settings,3.,None)
    original_audio=audio_key(clip,source,settings,3.)
    assert isinstance(original_video,dict) and isinstance(original_audio,dict)
    changed=copy.deepcopy(source)
    changed['fingerprint']['sha256']='different'
    assert video_key(clip,changed,settings,3.,None)!=original_video
    assert audio_key(clip,changed,settings,3.)!=original_audio
    result=add_bookends(timeline,analysis,tmp_path/'analysis')
    card=result['clips'][0];src=result['sources'][card['source_id']]
    original=video_key(card,src,result['settings'],4.,None)
    card['card_fade_in']=.7
    assert video_key(card,src,result['settings'],4.,None)!=original
