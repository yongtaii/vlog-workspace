"""Story phases, capture chronology, location ties and restraint with still photos."""
from datetime import datetime, timezone, timedelta

PHASES = ["opening", "journey", "explore", "highlight", "closing"]


def capture_order(value, assumed_timezone='+09:00'):
    if not value:
        return float('inf')
    try:
        stamp = datetime.fromisoformat(value.replace('Z','+00:00'))
        if stamp.tzinfo is None:
            sign = -1 if assumed_timezone.startswith('-') else 1
            hours,minutes = map(int,assumed_timezone[1:].split(':'))
            stamp = stamp.replace(tzinfo=timezone(sign*timedelta(hours=hours,minutes=minutes)))
        return stamp.timestamp()
    except (TypeError,ValueError):
        return float('inf')


def arrange(clips, assumed_timezone='+09:00'):
    return sorted(clips, key=lambda c: (PHASES.index(c['phase']),capture_order(c.get('capture_time'),assumed_timezone) + (c['start'] if c.get('kind','video')=='video' else 0),
                   str(c.get('location') or ''),c['source_order'],c['start']))


def separate_photos(clips):
    selected,rejected = [],[]
    for clip in clips:
        if selected and clip.get('kind')=='photo' and selected[-1].get('kind')=='photo':
            rejected.append({**clip,'reason':['consecutive_photo_deferred']})
        else:
            selected.append(clip)
    return selected,rejected


def place(clips):
    position = 0.
    for clip in clips:
        clip['timeline_start'] = round(position,4)
        position += clip['end']-clip['start']
    return round(position,4)
