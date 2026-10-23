"""Local photo metadata, orientation-safe derivatives and explicit story selection."""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageFilter

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from .common import digest, fingerprint
from .story import PHASES

PHOTO_EXTENSIONS = {'.jpg','.jpeg','.png','.webp','.tif','.tiff','.bmp','.heic','.heif'}


def oriented_photo(path):
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert('RGB')


def analyze_photo(path, input_dir, destination, config):
    from .analyze import phash
    with Image.open(path) as image:
        exif = image.getexif()
        detail = exif.get_ifd(34665) if 34665 in exif else {}
        gps = exif.get_ifd(34853) if 34853 in exif else {}
        taken = detail.get(36867) or exif.get(36867) or exif.get(306)
        offset = detail.get(36881) or exif.get(36881)
        if taken:
            # EXIF calendar fields use colons; retain unknown timezone rather than invent it.
            taken = str(taken)[:10].replace(':','-') + 'T' + str(taken)[11:19] + (str(offset) if offset else '')
        def coordinate(value, ref):
            deg, minute, second = map(float,value)
            return (deg + minute/60 + second/3600) * (-1 if ref in ('S','W',b'S',b'W') else 1)
        location = None
        if all(k in gps for k in (1,2,3,4)):
            location = {'latitude':coordinate(gps[2],gps[1]),'longitude':coordinate(gps[4],gps[3])}
        raw_size = image.size
        orientation = exif.get(274,1)
    picture = oriented_photo(path)
    width,height = picture.size
    picture.thumbnail((640,360))
    destination.mkdir(parents=True,exist_ok=True)
    frame = destination/'photo.jpg'
    picture.save(frame, quality=92)
    gray = cv2.cvtColor(np.array(picture),cv2.COLOR_RGB2GRAY)
    sample = {'time':0.,'frame':str(frame),'sharpness':float(cv2.Laplacian(gray,cv2.CV_64F).var()),
              'exposure':float(gray.mean()/255),'hash':phash(gray),'shake':0.,'motion':0.,'tracked':0}
    relative = str(path.relative_to(input_dir))
    return {'id':digest(relative)[:12],'path':str(path.resolve()),'relative_path':relative,'kind':'photo',
            'width':raw_size[0],'height':raw_size[1],'display_width':width,'display_height':height,
            'exif_orientation':orientation,'orientation':'portrait' if height>width else 'landscape',
            'creation_time':taken,'gps':location,'audio':[],'video_stream':0,
            'duration':float(config.get('photo_seconds',3)), 'fingerprint':fingerprint(path),
            'samples':[sample],'contact_sheets':[str(frame)]}


def choose_photos(analysis, hints, video_candidates, config):
    from .selection import distance
    selected, rejected = [], []
    for index, photo in enumerate(analysis.get('photos',[])):
        hint = hints.get(photo['relative_path'],{})
        reason = None
        if not hint.get('use') or not str(hint.get('reason','')).strip():
            reason = 'photo_requires_story_reason'
        elif hint.get('exclude'):
            reason = 'manual_exclusion'
        elif any((hint.get('event') and c.get('event') == hint['event']) or
                 any(distance(photo['samples'][0]['hash'],h)<=config['duplicate_distance'] for h in c['hashes'])
                 for c in video_candidates):
            reason = 'equivalent_video_preferred'
        elif any(distance(photo['samples'][0]['hash'],p['hashes'][0])<=config['duplicate_distance'] for p in selected):
            reason = 'duplicate_photo'
        duration = hint.get('display_seconds',config.get('photo_seconds',3.))
        if not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:
            raise ValueError('Photo display_seconds must be positive and finite')
        phase = hint.get('phase','explore')
        if phase not in PHASES:
            raise ValueError(f'Unknown story phase: {phase}')
        candidate = {'id':photo['id']+'-photo','source_id':photo['id'],'source':photo['path'],'kind':'photo',
            'start':0.,'end':float(duration),'phase':phase,'source_order':len(analysis['videos'])+index,
            'capture_time':hint.get('capture_time',photo.get('creation_time')),
            'location':hint.get('location') or photo.get('gps'),'event':hint.get('event'),
            'caption':hint.get('caption',''),'tags':hint.get('tags',[]),'hashes':[photo['samples'][0]['hash']],
            'photo_motion':hint.get('motion','none'),'photo_background':hint.get('background','blur'),
            'reason':[hint.get('reason','')], 'metrics':photo['samples'][0]}
        if reason:
            candidate['reason']=[reason]
            rejected.append(candidate)
        else:
            selected.append(candidate)
    return selected,rejected


def prepare_canvas(source, settings, clip, destination):
    """Contain the entire subject; movement operates only within protective margins."""
    image = oriented_photo(source)
    w,h = settings['width'],settings['height']
    if clip.get('photo_background','blur')=='blur':
        background = ImageOps.fit(image,(w,h)).filter(ImageFilter.GaussianBlur(max(w,h)/35))
        background = Image.blend(background,Image.new('RGB',(w,h),'black'),.25)
    else:
        background = Image.new('RGB',(w,h),'black')
    # Motion zooms/pans the padded canvas, never beyond the full foreground's safe bounds.
    factor = .90 if clip.get('photo_motion','none')!='none' else 1.
    foreground = ImageOps.contain(image,(max(1,int(w*factor)),max(1,int(h*factor))))
    background.paste(foreground,((w-foreground.width)//2,(h-foreground.height)//2))
    background.save(destination)
