"""Reusable dated opening and closing scenes, generated locally from existing imagery."""
from __future__ import annotations

import copy
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from .common import digest, fingerprint, local_file, protect_output
from .photos import oriented_photo
from .story import place

ARTWORK_VERSION = 2
DEFAULTS = {'enabled': True, 'title': '일상의 기록', 'ending': '오늘도, 좋은 하루.',
            'opening_seconds': 4.0, 'closing_seconds': 4.0, 'date_text': None, 'font': None}


def capture_date(clips, assumed_timezone='+09:00'):
    sign = -1 if assumed_timezone.startswith('-') else 1
    hours, minutes = map(int, assumed_timezone[1:].split(':'))
    local_zone = timezone(sign * timedelta(hours=hours, minutes=minutes))
    dates = []
    for clip in clips:
        if not clip.get('capture_time'):
            continue
        try:
            stamp = datetime.fromisoformat(clip['capture_time'].replace('Z', '+00:00'))
            stamp = stamp.replace(tzinfo=local_zone) if stamp.tzinfo is None else stamp.astimezone(local_zone)
            dates.append(stamp.date())
        except (ValueError, TypeError):
            continue
    if not dates:
        return '날짜 미상'
    first, last = min(dates), max(dates)
    return first.strftime('%Y.%m.%d') if first == last else f'{first:%Y.%m.%d} — {last:%Y.%m.%d}'


def find_font(configured=None, text='일상의 기록'):
    candidates = [Path(configured)] if configured else [
        Path('/System/Library/Fonts/AppleSDGothicNeo.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        Path('/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf'),
        Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')]
    for candidate in candidates:
        if candidate.is_file():
            font = ImageFont.truetype(str(candidate), 32)
            missing = bytes(font.getmask('\uffff'))
            if all(ch.isspace() or bytes(font.getmask(ch)) != missing for ch in set(text)):
                return candidate.resolve()
    raise ValueError('Title/ending require a local font supporting the text; set settings.bookends.font')


def background_path(clip, source, analysis):
    if source.get('kind') == 'photo':
        return local_file(source['path'])
    media = next((v for v in analysis['videos'] if v['id'] == clip['source_id']), None)
    if not media or not media['samples']:
        raise ValueError('Analyze video frames before generating opening/closing scenes')
    target = clip['start'] + min(1.5, (clip['end'] - clip['start']) / 2)
    return local_file(min(media['samples'], key=lambda s: abs(s['time'] - target))['frame'])


def artwork(background, text, date, role, font_path, size):
    w, h = size
    scale = w / 1920
    original = oriented_photo(background)
    portrait = original.height > original.width
    image = ImageOps.fit(original, (w, h)).filter(ImageFilter.GaussianBlur((24 if portrait else 5) * scale))
    if portrait:
        # Preserve the complete portrait on the right; the enlarged image is decorative background only.
        panel = ImageOps.contain(original, (int(w * .44), int(h * .84)))
        image.paste(panel, (int(w * .52) + (int(w * .44) - panel.width) // 2, (h - panel.height) // 2))
    # A quiet left-to-right shade keeps type readable without hiding the whole image.
    shade = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(shade)
    for x in range(w):
        alpha = int(192 - 90 * x / max(1, w - 1)) if role == 'opening' else 177
        draw.line((x, 0, x, h), fill=(14, 24, 30, alpha))
    image = Image.alpha_composite(image.convert('RGBA'), shade)
    draw = ImageDraw.Draw(image)
    cream, muted, gold = '#fff7e9', '#d8dedc', '#dfc396'
    left, baseline = int(w * .10), int(h * .37)
    small = ImageFont.truetype(str(font_path), max(12, round(28 * scale)))
    date_font = ImageFont.truetype(str(font_path), max(16, round(42 * scale)))
    label = 'DAILY VLOG' if role == 'opening' else 'END OF THE DAY'
    draw.text((left, baseline - int(92 * scale)), label, font=small, fill=gold)
    title_size = max(20, round(100 * scale))
    while True:
        title_font = ImageFont.truetype(str(font_path), title_size)
        box = draw.multiline_textbbox((0, 0), text, font=title_font, spacing=int(18 * scale))
        if box[2] - box[0] <= w * .8 and box[3] - box[1] <= h * .36:
            break
        title_size -= 2
        if title_size < 16:
            raise ValueError('Opening/ending text is too long; shorten or use line breaks')
    draw.multiline_text((left, baseline - box[1]), text, font=title_font, fill=cream, spacing=int(18 * scale))
    y = baseline + (box[3] - box[1]) + int(64 * scale)
    draw.line((left, y, left + int(94 * scale), y), fill=gold, width=max(1, round(3 * scale)))
    draw.text((left, y + int(34 * scale)), date, font=date_font, fill=muted)
    return image.convert('RGB')


def add_bookends(timeline, analysis, analysis_dir, overrides=None):
    timeline = copy.deepcopy(timeline)
    options = {**DEFAULTS, **timeline['settings'].get('bookends', {}), **(overrides or {})}
    timeline['settings']['bookends'] = options
    generated = [c for c in timeline['clips'] if c.get('bookend_role') in ('opening', 'closing')]
    body = [c for c in timeline['clips'] if c not in generated]
    if not body:
        raise ValueError('Opening/ending require at least one body shot')
    used = {c['source_id'] for c in body}
    used.update(c['ambient']['source_id'] for c in body if c.get('ambient'))
    for clip in generated:
        if clip['source_id'] not in used:
            timeline['sources'].pop(clip['source_id'], None)
    if not options['enabled']:
        timeline['clips'] = body
        timeline['duration'] = place(body)
        return timeline
    # A separate opening/ending supersedes older title overlays on boundary body shots.
    if body[0].get('card', {}).get('style') == 'title':
        body[0].pop('card')
    if body[-1].get('card', {}).get('style') == 'ending':
        body[-1].pop('card')
    directory = protect_output(Path(analysis_dir) / 'generated/bookends', timeline['input_dir'])
    originals = [Path(s['path']).resolve() for s in timeline['sources'].values()]
    if any(directory == p or directory in p.parents for p in originals):
        raise ValueError('Generated title directory must not contain original media')
    date = options['date_text'] or capture_date(body, timeline['settings'].get('capture_timezone', '+09:00'))
    font_path = find_font(options['font'], options['title'] + options['ending'] + date)
    settings = timeline['settings']
    cards = []
    for role, anchor in (('opening', body[0]), ('closing', body[-1])):
        text = options['title'] if role == 'opening' else options['ending']
        seconds = options[role + '_seconds']
        if not isinstance(seconds, (int, float)) or not 0 < seconds <= 30:
            raise ValueError('Opening/ending duration must be in (0,30] seconds')
        background = background_path(anchor, timeline['sources'][anchor['source_id']], analysis)
        signature = {'artwork_version': ARTWORK_VERSION, 'role': role, 'text': text, 'date': date,
                     'background': fingerprint(background), 'font': fingerprint(font_path),
                     'size': [settings['width'], settings['height']]}
        dest = directory / digest(signature) / f'{role}.png'
        dest.parent.mkdir(parents=True, exist_ok=True)
        picture = artwork(background, text, date, role, font_path, (settings['width'], settings['height']))
        buffer = BytesIO()
        picture.save(buffer, format='PNG')
        content = buffer.getvalue()
        if not dest.exists() or dest.read_bytes() != content:
            dest.write_bytes(content)
        source_id = 'generated-bookend-' + role
        timeline['sources'][source_id] = {'kind': 'card', 'path': str(dest), 'duration': seconds,
            'video_stream': 0, 'audio': [], 'fingerprint': fingerprint(dest), 'color_transfer': None}
        card = {'id': 'bookend-' + role, 'source_id': source_id, 'source': str(dest), 'kind': 'card',
                'bookend_role': role, 'title_text': text, 'date_text': date, 'start': 0., 'end': seconds,
                'phase': role if role == 'opening' else 'closing', 'caption': '', 'tags': ['타이틀' if role == 'opening' else '엔딩'],
                'card_fade_in': .4, 'card_fade_out': .75 if role == 'closing' else .25,
                'photo_background': 'pad', 'photo_motion': 'none',
                'reason': ['선정 장면을 배경으로 만든 날짜 포함 오프닝' if role == 'opening' else '하루의 기록을 마무리하는 엔딩'],
                'metrics': {'generated': True, 'date_source': 'user' if options['date_text'] else 'capture_metadata'}}
        # Keep the same low-level real ambience, if available, with gentle scene fades.
        ambient = anchor.get('ambient')
        if ambient:
            card['ambient'] = {**ambient, 'volume': min(.08, ambient.get('volume', .08))}
        elif timeline['sources'][anchor['source_id']]['audio']:
            source = timeline['sources'][anchor['source_id']]
            start = anchor['start']
            end = min(source['duration'], start + seconds)
            card['ambient'] = {'source_id': anchor['source_id'], 'start': start, 'end': end, 'volume': .08}
        cards.append(card)
    timeline['clips'] = [cards[0], *body, cards[1]]
    timeline['duration'] = place(timeline['clips'])
    return timeline
