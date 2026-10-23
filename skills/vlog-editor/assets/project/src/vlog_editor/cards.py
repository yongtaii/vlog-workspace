"""Opening title and ending cards: text overlaid on a real shot, with fades to/from black."""
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .common import local_file

STYLES = ("title", "ending")
# Fade lengths in seconds; the shot itself stays real footage or a real photo.
TITLE_FADE_IN, ENDING_FADE_OUT, TEXT_FADE = .8, 1.2, .6


def card_font(settings):
    path = settings.get("title_font") or settings.get("font")
    if not path:
        raise ValueError("Title/ending cards require settings.title_font or settings.font with a local Korean font")
    return local_file(path), int(settings.get("title_font_index", 0) or 0)


def validate_card(card, duration, settings):
    if not isinstance(card, dict) or card.get("style") not in STYLES:
        raise ValueError("card.style must be title or ending")
    if not isinstance(card.get("title"), str) or not card["title"].strip():
        raise ValueError("card.title must be nonempty text")
    if not isinstance(card.get("subtitle", ""), str):
        raise ValueError("card.subtitle must be text")
    seconds = card.get("seconds", duration)
    if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("card.seconds must be a finite positive number")
    index = settings.get("title_font_index", 0)
    if not isinstance(index, int) or index < 0:
        raise ValueError("title_font_index must be a nonnegative integer")
    card_font(settings)


def text_window(card, duration):
    """Seconds [start, end) where the text is visible: title opens the shot, ending closes it."""
    seconds = min(float(card.get("seconds", duration)), duration)
    return (0., seconds) if card["style"] == "title" else (duration - seconds, duration)


def overlay_filter(card, duration, label_in, label_out):
    start, end = text_window(card, duration)
    fade = min(TEXT_FADE, (end - start) / 3)
    lead = min(.4, (end - start) / 4) if card["style"] == "title" else 0.
    chain = [f"format=rgba", f"fade=t=in:st={start + lead:.4f}:d={fade:.4f}:alpha=1"]
    if card["style"] == "title":
        chain.append(f"fade=t=out:st={max(start, end - fade):.4f}:d={fade:.4f}:alpha=1")
    return f"[{label_in}]" + ",".join(chain) + f"[{label_out}]"


def black_fades(card, duration):
    """Video fades applied after the overlay so text and picture move together."""
    if card["style"] == "title":
        return [f"fade=t=in:st=0:d={min(TITLE_FADE_IN, duration / 3):.4f}"]
    fade = min(ENDING_FADE_OUT, duration / 3)
    return [f"fade=t=out:st={duration - fade:.4f}:d={fade:.4f}"]


def audio_fades(card, duration):
    if card["style"] == "title":
        return [f"afade=t=in:d={min(TITLE_FADE_IN, duration / 3):.4f}"]
    fade = min(ENDING_FADE_OUT, duration / 3)
    return [f"afade=t=out:st={duration - fade:.4f}:d={fade:.4f}"]


def draw_card(card, settings, destination):
    w, h = settings["width"], settings["height"]
    path, index = card_font(settings)
    title_font = ImageFont.truetype(str(path), max(12, int(h * .085)), index=index)
    sub_font = ImageFont.truetype(str(path), max(10, int(h * .034)), index=index)
    # Soft dim keeps white text readable on bright footage without hiding the scene.
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 70 if card["style"] == "title" else 105))
    text = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text)
    title, subtitle = card["title"].strip(), card.get("subtitle", "").strip()
    tb = draw.multiline_textbbox((0, 0), title, font=title_font, spacing=12, align="center")
    sb = draw.multiline_textbbox((0, 0), subtitle, font=sub_font, spacing=8, align="center") if subtitle else (0, 0, 0, 0)
    gap = int(h * .03) if subtitle else 0
    tw, th, sw, sh = tb[2] - tb[0], tb[3] - tb[1], sb[2] - sb[0], sb[3] - sb[1]
    margin = int(w * .06)
    if max(tw, sw) > w - margin * 2 or th + gap + sh > h - margin * 2:
        raise ValueError("Card text exceeds the frame; shorten it or add line breaks")
    top = (h - (th + gap + sh)) / 2
    positions = [((w - tw) / 2 - tb[0], top - tb[1], title, title_font, 12)]
    if subtitle:
        positions.append(((w - sw) / 2 - sb[0], top + th + gap - sb[1], subtitle, sub_font, 8))
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    for x, y, value, font, spacing in positions:
        shadow_draw.multiline_text((x, y + 3), value, font=font, fill=(0, 0, 0, 170), spacing=spacing, align="center")
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, h // 180)))
    for x, y, value, font, spacing in positions:
        fill = "white" if value == title else (235, 235, 235, 255)
        draw.multiline_text((x, y), value, font=font, fill=fill, spacing=spacing, align="center")
    Image.alpha_composite(Image.alpha_composite(layer, shadow), text).save(destination)
