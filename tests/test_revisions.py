import copy
import json
from pathlib import Path

import pytest

from vlog_editor.cache import Cache
from vlog_editor.common import ROOT, digest
from vlog_editor.revision import apply_patch
from vlog_editor.storyboard import write_storyboard


@pytest.fixture
def timeline():
    config = json.loads((ROOT/'config.json').read_text())
    return {'version':1,'input_dir':'/fixture','settings':config,'sources':{
        'src':{'path':'/fixture/a.mp4','duration':10}},'clips':[
        {'id':name,'source_id':'src','source':'/fixture/a.mp4','start':start,'end':end,'phase':'explore'}
        for name,start,end in [('one',0,3),('two',3,6),('three',6,9)]]}


def patch(timeline, operations):
    return {'version':1,'base_digest':digest(timeline),'operations':operations}


def test_trim_caption_move_and_audio_are_independent(timeline):
    before=copy.deepcopy(timeline)
    changed=apply_patch(timeline,patch(timeline,[
        {'op':'trim','clip_id':'two','start':3,'end':5},
        {'op':'caption','clip_id':'two','text':'작은 순간'},
        {'op':'audio_gain','clip_id':'two','value':.5},
        {'op':'move_before','clip_id':'three','before_id':'one'}]))
    assert [c['id'] for c in changed['clips']]==['three','one','two']
    assert changed['duration']==8 and changed['clips'][2]['timeline_start']==6
    assert changed['clips'][2]['caption']=='작은 순간'
    assert changed['clips'][2]['source_volume']==.5
    assert timeline==before


@pytest.mark.parametrize('operations',[
    [{'op':'trim','clip_id':'two','start':3,'end':30}],
    [{'op':'move_before','clip_id':'two','before_id':'missing'}],
    [{'op':'setting','key':'source_volume','value':-1}],
    [{'op':'setting','key':'music','value':'https://external.invalid/music.wav'}],
    [{'op':'remove','clip_id':name} for name in ('one','two','three')]
])
def test_invalid_edits_do_not_modify_original_timeline(timeline,operations):
    before=copy.deepcopy(timeline)
    with pytest.raises((ValueError,KeyError)):
        apply_patch(timeline,patch(timeline,operations))
    assert timeline==before


def test_stale_revision_rejected(timeline):
    old=patch(timeline,[{'op':'remove','clip_id':'one'}])
    timeline['clips'][0]['caption']='edited elsewhere'
    with pytest.raises(ValueError,match='base_digest'):
        apply_patch(timeline,old)


def test_cache_detects_corruption_and_reuses_valid_file(tmp_path):
    cache=Cache(tmp_path,'test-encoder')
    calls=[]
    def builder(path):
        calls.append(path)
        path.write_bytes(b'good artifact')
    artifact=cache.get('video',{'start':1},'.mp4',builder)
    cache.get('video',{'start':1},'.mp4',builder)
    assert len(calls)==1
    artifact.write_bytes(b'broken')
    cache.get('video',{'start':1},'.mp4',builder)
    assert len(calls)==2 and artifact.read_bytes()==b'good artifact'


def test_storyboard_escapes_text_and_links_local_frames(tmp_path):
    source=tmp_path/'input'
    source.mkdir()
    frames=tmp_path/'frames'
    frames.mkdir()
    frame=frames/'sample with spaces.jpg'
    frame.write_bytes(b'fixture')
    analysis={'input_dir':str(source),'videos':[{'id':'src','path':str(source/'a.mp4'),
        'relative_path':'<script>alert(1)</script>.mp4','duration':3,'orientation':'portrait','audio':[],
        'samples':[{'time':1,'frame':str(frame)}],'contact_sheets':[str(frame)]}]}
    output=write_storyboard(analysis,None,tmp_path/'work/storyboard.html')
    html=output.read_text()
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert '../frames/sample%20with%20spaces.jpg' in html


FONT='/System/Library/Fonts/AppleSDGothicNeo.ttc'


@pytest.mark.skipif(not Path(FONT).exists(), reason='macOS Korean font fixture')
def test_title_and_ending_cards_and_insert(timeline):
    before=copy.deepcopy(timeline)
    changed=apply_patch(timeline,patch(timeline,[
        {'op':'setting','key':'title_font','value':FONT},
        {'op':'setting','key':'title_font_index','value':6},
        {'op':'insert','clip':{'id':'ending','source_id':'src','start':9,'end':10,'phase':'closing'},'before_id':None},
        {'op':'card','clip_id':'one','value':{'style':'title','title':'우리의 하루','subtitle':'2026.10.04','seconds':2}},
        {'op':'card','clip_id':'ending','value':{'style':'ending','title':'끝'}}]))
    assert [c['id'] for c in changed['clips']]==['one','two','three','ending']
    assert changed['clips'][-1]['source']=='/fixture/a.mp4' and changed['duration']==10
    assert changed['clips'][0]['card']['style']=='title'
    assert timeline==before
    removed=apply_patch(changed,patch(changed,[{'op':'card','clip_id':'one','value':None}]))
    assert 'card' not in removed['clips'][0]


@pytest.mark.parametrize('card',[
    {'style':'opening','title':'x'}, {'style':'title','title':' '}, {'style':'ending','title':'x','seconds':-1}])
def test_invalid_cards_rejected(timeline,card):
    timeline['settings']['title_font']=FONT
    with pytest.raises(ValueError):
        apply_patch(timeline,patch(timeline,[{'op':'card','clip_id':'one','value':card}]))


def test_card_without_font_rejected(timeline):
    with pytest.raises(ValueError,match='font'):
        apply_patch(timeline,patch(timeline,[{'op':'card','clip_id':'one','value':{'style':'title','title':'하루'}}]))


@pytest.mark.skipif(not Path(FONT).exists(), reason='macOS Korean font fixture')
def test_card_image_fits_frame(tmp_path):
    from PIL import Image
    from vlog_editor.cards import draw_card
    settings={'width':1920,'height':1080,'title_font':FONT,'title_font_index':6}
    draw_card({'style':'title','title':'우리의 하루','subtitle':'2026.10.04'},settings,tmp_path/'card.png')
    image=Image.open(tmp_path/'card.png')
    assert image.size==(1920,1080) and image.mode=='RGBA'
    with pytest.raises(ValueError,match='exceeds'):
        draw_card({'style':'title','title':'아주 긴 제목 '*12},settings,tmp_path/'long.png')
