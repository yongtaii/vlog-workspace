#!/usr/bin/env python3
"""Create mixed photo/video synthetic fixtures and verify source safety and incremental edits."""
import argparse
from pathlib import Path
from shutil import copy2
import wave

from PIL import Image, ImageDraw
from vlog_editor.cli import main
from vlog_editor.common import ROOT, digest, fingerprint, read_json, run, write_json


def main_test():
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,default=ROOT/'analysis/photo-smoke')
    parser.add_argument('--video-fixtures',type=Path,required=True,help='New video smoke project')
    args=parser.parse_args()
    root=args.directory.resolve()
    if root.exists():
        raise SystemExit(f'Refusing to overwrite existing test project: {root}')
    (root/'input/videos').mkdir(parents=True)
    (root/'input/photos').mkdir()
    (root/'music').mkdir()
    config=read_json(ROOT/'config.json')
    config.update(width=640,height=360,fps=24,preset='ultrafast',clip_seconds=6,target_seconds=42,
                  min_sharpness=10,max_shake=.15,duplicate_distance=0,scene_threshold=.9)
    config['bookends'] = {'enabled': False}
    hints={}
    for index,source in enumerate(sorted((args.video_fixtures/'input/videos').glob('*.mp4'))):
        dest=root/'input/videos'/source.name
        copy2(source,dest)
        hints['videos/'+dest.name]={'phase':'explore','capture_time':f'2026-10-23T09:{index*2:02}:00+09:00',
                                   'location':'테스트 도시','event':f'video-{index}'}
    # White perimeter makes accidental foreground cropping apparent on visual review.
    for index,(size,minute) in enumerate((((300,500),3),((600,400),9))):
        image=Image.new('RGB',size,(40+index*150,80,160-index*80))
        draw=ImageDraw.Draw(image)
        draw.rectangle((2,2,size[0]-3,size[1]-3),outline='white',width=10)
        draw.ellipse((size[0]*.2,size[1]*.2,size[0]*.8,size[1]*.8),fill='yellow' if index==0 else 'cyan')
        path=root/f'input/photos/memory-{index}.jpg'
        exif=Image.Exif()
        exif[306]=f'2026:10:23 09:{minute:02}:00'
        image.save(path,exif=exif,quality=95)
        hints[f'photos/{path.name}']={'use':True,'reason':'동영상에 없는 기념 순간','location':'테스트 도시',
                                    'motion':'zoom' if index==0 else 'pan','background':'blur' if index==0 else 'pad'}
    # A high-quality photo with no story justification stays out despite remaining budget.
    copy2(root/'input/photos/memory-0.jpg',root/'input/photos/not-needed.jpg')
    music=root/'music/bgm.wav'
    run(['ffmpeg','-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=220:duration=4',str(music)])
    config['music']='music/bgm.wav'
    write_json(root/'config.json',config)
    write_json(root/'hints.json',hints)
    originals=list((root/'input').rglob('*.mp4'))+list((root/'input').rglob('*.jpg'))+[music]
    before={str(p):fingerprint(p) for p in originals}
    assert main(['--project',str(root),'run','--hints','hints.json'])==0
    timeline=read_json(root/'analysis/timeline.json')
    photos=[c for c in timeline['clips'] if c['kind']=='photo']
    assert len(photos)==2 and timeline['duration']==42
    assert all(not(a['kind']==b['kind']=='photo') for a,b in zip(timeline['clips'],timeline['clips'][1:]))
    assert any('photo_requires_story_reason' in c['reason'] for c in timeline['rejected'])
    assert all(p.get('ambient') for p in photos)
    # A still image style edit only replaces its video shot, not the audio/ambience.
    patch={'version':1,'base_digest':digest(timeline),'operations':[
        {'op':'photo_style','clip_id':photos[0]['id'],'motion':'pan','background':'blur'}]}
    write_json(root/'analysis/patch.json',patch)
    assert main(['--project',str(root),'revise','--patch','analysis/patch.json','--request','첫 사진만 미세한 패닝으로 바꿔줘','--render'])==0
    events=read_json(root/'preview/preview-validation.json')['cache']+read_json(root/'output/full-validation.json')['cache']
    misses={kind:sum(e['kind']==kind and e['status']=='rendered' for e in events) for kind in ('video','audio','mix')}
    assert misses=={'video':1,'audio':0,'mix':0},misses
    timeline_after = read_json(root/'analysis/timeline.json')
    patch={'version':1,'base_digest':digest(timeline_after),'operations':[
        {'op':'photo_duration','clip_id':photos[-1]['id'],'seconds':4.}]}
    write_json(root/'analysis/patch.json',patch)
    assert main(['--project',str(root),'revise','--patch','analysis/patch.json','--request','마지막 사진을 4초로 늘려줘','--render'])==0
    assert read_json(root/'analysis/timeline.json')['duration']==43.
    # Inspect the actual cached photo sound: no silent gap when ambience exists.
    from vlog_editor.sound import audio_key
    from vlog_editor.cache import Cache
    clip=photos[0]
    src=timeline['sources'][clip['source_id']]
    ambient=timeline['sources'][clip['ambient']['source_id']]
    cache=Cache(root/'analysis/cache',run(['ffmpeg','-version']).splitlines()[0])
    path=cache.get('audio',audio_key(clip,src,timeline['settings'],3.,ambient),'.wav',lambda _:None)
    with wave.open(str(path)) as sound:
        assert any(sound.readframes(sound.getnframes())), 'Photo ambience is unexpectedly silent'
    assert before=={p:fingerprint(p) for p in before}
    run(['ffmpeg','-v','error','-nostdin','-y','-ss','13','-i',str(root/'output/vlog.mp4'),'-frames:v','1',str(root/'output/photo-review.jpg')])
    write_json(root/'output/photo-validation.json',{'passed':True,'photo_count':2,'initial_duration':42,'final_duration':43,
        'source_hashes_unchanged':True,'photo_style_revision_misses':misses,'ambience_non_silent':True})
    print(f'Mixed photo/video integration passed: {root}')


if __name__=='__main__':
    main_test()
