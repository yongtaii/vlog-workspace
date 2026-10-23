from pathlib import Path
import copy
import json

import pytest
from PIL import Image

from vlog_editor.common import ROOT, fingerprint
from vlog_editor.photos import analyze_photo, prepare_canvas, choose_photos
from vlog_editor.story import arrange, separate_photos
from vlog_editor.validation import validate_timeline


@pytest.fixture
def config():
    return json.loads((ROOT/'config.json').read_text())


def test_exif_orientation_and_time_do_not_change_original(tmp_path,config):
    root=tmp_path/'input'
    root.mkdir()
    photo=root/'portrait.jpg'
    exif=Image.Exif()
    exif[274]=6
    exif[306]='2026:10:23 09:10:11'
    Image.new('RGB',(120,80),'red').save(photo,exif=exif)
    before=fingerprint(photo)
    meta=analyze_photo(photo,root,tmp_path/'analysis/frame',config)
    assert (meta['display_width'],meta['display_height'])==(80,120)
    assert meta['creation_time']=='2026-10-23T09:10:11'
    assert before==fingerprint(photo)


def test_photos_need_story_reason_and_video_equivalence_wins(config):
    base={'id':'p','path':'/input/p.jpg','relative_path':'photos/p.jpg','creation_time':None,'gps':None,
          'samples':[{'hash':'0000000000000000'}]}
    analysis={'videos':[],'photos':[base]}
    selected,rejected=choose_photos(analysis,{},[],config)
    assert not selected and rejected[0]['reason']==['photo_requires_story_reason']
    hints={'photos/p.jpg':{'use':True,'reason':'영상에 없는 기념사진','event':'group'}}
    selected,_=choose_photos(analysis,hints,[],config)
    assert len(selected)==1 and selected[0]['end']==3
    selected,rejected=choose_photos(analysis,hints,[{'event':'group','hashes':['ffffffffffffffff']}],config)
    assert not selected and rejected[0]['reason']==['equivalent_video_preferred']


def test_photo_sequence_respects_capture_time_and_avoids_consecutive():
    clips=[{'id':'later','kind':'video','capture_time':'2026-10-23T01:00:00Z','phase':'explore','source_order':0,'start':0},
           {'id':'photo','kind':'photo','capture_time':'2026-10-23T09:30:00','phase':'explore','source_order':1,'start':0},
           {'id':'photo2','kind':'photo','capture_time':'2026-10-23T09:40:00','phase':'explore','source_order':2,'start':0}]
    ordered=arrange(clips)
    assert [c['id'] for c in ordered]==['photo','photo2','later']
    selected,rejected=separate_photos(ordered)
    assert [c['id'] for c in selected]==['photo','later'] and len(rejected)==1


def test_vertical_photo_keeps_foreground_corners(tmp_path,config):
    source=tmp_path/'original.png'
    image=Image.new('RGB',(100,200),'red')
    for point,color in [((0,0),'white'),((99,0),'blue'),((0,199),'green'),((99,199),'yellow')]:
        image.putpixel(point,Image.new('RGB',(1,1),color).getpixel((0,0)))
    image.save(source)
    config.update(width=200,height=100)
    prepare_canvas(source,config,{'photo_background':'pad','photo_motion':'none'},tmp_path/'canvas.png')
    with Image.open(tmp_path/'canvas.png') as canvas:
        assert canvas.size==(200,100)
        # The complete 1:2 foreground is contained, with side padding.
        assert canvas.getpixel((0,50))==(0,0,0)
        assert canvas.getpixel((100,50))==(255,0,0)
    assert Image.open(source).size==(100,200)


def test_photo_duration_is_display_time_not_source_video_bounds(config):
    timeline={'version':1,'input_dir':'/input','settings':config,'sources':{'p':{'kind':'photo','path':'/input/p.jpg','duration':3}},
              'clips':[{'id':'p1','source_id':'p','source':'/input/p.jpg','kind':'photo','start':0,'end':4}]}
    validate_timeline(timeline)
    assert timeline['duration']==4
    timeline['clips'][0]['start']=1
    with pytest.raises(ValueError,match='start'):
        validate_timeline(timeline)


def test_capture_order_adds_video_clip_offset():
    clips=[{'id':'video','kind':'video','capture_time':'2026-10-23T09:00:00+09:00',
            'phase':'explore','source_order':0,'start':300},
           {'id':'photo','kind':'photo','capture_time':'2026-10-23T09:01:00+09:00',
            'phase':'explore','source_order':1,'start':0}]
    assert [c['id'] for c in arrange(clips)]==['photo','video']


def test_photo_ambience_stays_within_rounded_video_duration(config):
    from vlog_editor.planner import make_timeline
    from vlog_editor.validation import validate_timeline
    config.update(clip_seconds=7, target_seconds=None)
    video = {'id':'v','path':'/fixture/v.mp4','relative_path':'videos/v.mp4','duration':8.466667,'video_stream':0,
             'audio':[{'index':1}],'fingerprint':{},'creation_time':'2026-10-04T07:28:14Z',
             'scenes':[{'start':0,'end':8.466667}],
             'samples':[{'time':t,'sharpness':200,'shake':0,'tracked':40,'motion':.005,'exposure':.5,'hash':'0000000000000000'} for t in (0,2,4,6,8)]}
    photo = {'id':'p','path':'/fixture/p.jpg','relative_path':'photos/p.jpg','kind':'photo','duration':3.,'video_stream':0,
             'audio':[],'fingerprint':{},'creation_time':'2026-10-04T16:30:00+09:00',
             'samples':[{'time':0,'hash':'ffffffffffffffff','sharpness':200,'exposure':.5}]}
    timeline = make_timeline({'input_dir':'/fixture','videos':[video],'photos':[photo]}, config,
                             {'photos/p.jpg':{'use':True,'reason':'영상에 없는 순간'}})
    ambient = timeline['clips'][-1]['ambient']
    assert ambient['end'] <= video['duration']
    validate_timeline(timeline)
