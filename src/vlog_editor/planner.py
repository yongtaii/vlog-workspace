"""Video-first selection with explicitly justified complementary still photos."""
from .common import digest
from .photos import choose_photos
from .selection import build_candidates, select_clips
from .story import arrange, place, separate_photos


def make_timeline(analysis, config, hints=None):
    hints = hints or {}
    candidates,rejected,videos = build_candidates(analysis,config,hints)
    photos,photo_rejected = choose_photos(analysis,hints,candidates,config)
    # Photos reserve time only after a human/agent (Codex or Claude) has recorded their story purpose.
    # Leave room for at least one video; never turn the vlog into a forced slideshow.
    approved,budget = [],float('inf') if config['target_seconds'] is None else float(config['target_seconds'])
    for photo in photos:
        length = photo['end']
        if length <= budget-1:
            approved.append(photo)
            budget -= length
        else:
            photo_rejected.append({**photo,'reason':['duration_budget']})
    video_config = {**config,'target_seconds':None if config['target_seconds'] is None else budget}
    selected,rejected = select_clips(candidates,rejected,video_config)
    selected,consecutive = separate_photos(arrange(selected+approved,config.get('capture_timezone','+09:00')))
    rejected += photo_rejected + consecutive
    sources = {v['id']:{'path':v['path'],'kind':v.get('kind','video'),'duration':v['duration'],
               'video_stream':v['video_stream'],'color_transfer':v.get('color_transfer'),'audio':v['audio'],'fingerprint':v['fingerprint']}
               for v in videos+analysis.get('photos',[])}
    # Keep a nearby known environment sound through a photo when available.
    # This is a short loop from the preceding selected shot, not invented audio.
    for index,clip in enumerate(selected):
        if clip.get('kind')=='photo':
            previous = next((c for c in reversed(selected[:index]) if c.get('kind','video')=='video'
                             and sources[c['source_id']]['audio']
                             and (not clip.get('location') or not c.get('location') or clip['location']==c['location'])),None)
            if previous:
                # Clip bounds are rounded to 4 decimals and may overshoot the probed duration slightly.
                end = min(previous['end'],sources[previous['source_id']]['duration'])
                start = max(previous['start'],end-2.)
                clip['ambient'] = {'source_id':previous['source_id'],'start':start,'end':end,'volume':.55}
    # Title/ending text comes only from hints written after reviewing the footage.
    for key,clip in (('@title',selected[0] if selected else None),('@ending',selected[-1] if selected else None)):
        if hints.get(key) and clip is not None:
            clip['card'] = {'style':key[1:],**hints[key]}
    position = place(selected)
    warnings = ['Semantic story understanding requires review of the storyboard and hints.',
                'Scene/quality checks use sparse samples. Photos without a recorded story reason are not inserted.',
                'Naive capture times use settings.capture_timezone; GPS is stored locally without geocoding.']
    if config['target_seconds'] is not None and position < config['target_seconds']-.1:
        warnings.append(f'Eligible footage is only {position:.2f}s; requested {config["target_seconds"]:.2f}s. No filler added.')
    return {'version':1,'input_dir':analysis['input_dir'],'analysis_digest':digest(analysis),
            'settings':config,'sources':sources,'clips':selected,'duration':position,'rejected':rejected,'warnings':warnings}
