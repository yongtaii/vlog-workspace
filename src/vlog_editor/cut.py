"""Silent video shots: trim, aspect-preserving normalization, color, captions, cuts."""
from PIL import Image, ImageDraw, ImageFont
from .cards import black_fades, draw_card, overlay_filter
from .photos import prepare_canvas
from .common import local_file, run

VIDEO_SETTINGS = ("width", "height", "fps", "preset", "crf", "transition", "transition_seconds", "color")


def video_key(clip, source, settings, duration, font_identity, card_font_identity=None):
    key = {"source": source["fingerprint"], "color_transfer": source.get("color_transfer"), "stream": source["video_stream"],
           "start": clip["start"], "duration": duration, "kind": source.get("kind", "video"),
           "photo_motion": clip.get("photo_motion", "none"), "photo_background": clip.get("photo_background", "blur"),
           "settings": {k: settings[k] for k in VIDEO_SETTINGS}, "caption": clip.get("caption", ""),
           "font": font_identity if clip.get("caption") else None,
           "subtitle_size": settings["subtitle_size"] if clip.get("caption") else None}
    if clip.get("card"):
        key["card"] = clip["card"]
        key["card_font"] = [card_font_identity, settings.get("title_font_index", 0)]
    if source.get("kind") == "card":
        key["card_render_version"] = 1
        key["card_fades"] = [clip.get("card_fade_in", .4), clip.get("card_fade_out", .75)]
    return key


def render_shot(clip, source, settings, duration, destination):
    vf = [f"scale={settings['width']}:{settings['height']}:force_original_aspect_ratio=decrease",
          f"pad={settings['width']}:{settings['height']}:(ow-iw)/2:(oh-ih)/2:color=black",
          "setsar=1", f"fps={settings['fps']}", "format=yuv420p", "setpts=PTS-STARTPTS"]
    if source.get('color_transfer')=='arib-std-b67':
        from .color import display_lut,hdr_filter
        vf.insert(0,hdr_filter(display_lut(destination.parent/'hlg-to-sdr.cube')))
    is_photo = source.get("kind") in ("photo", "card")
    if is_photo and clip.get("photo_motion","none")!="none":
        frames = max(1,round(duration*settings['fps'])-1)
        if clip['photo_motion']=='zoom':
            motion = f"zoompan=z='1+0.02*on/{frames}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
        else:
            motion = f"zoompan=z=1.02:x='(iw-iw/zoom)*on/{frames}':y='ih/2-ih/zoom/2'"
        vf.insert(0,motion+f":d=1:s={settings['width']}x{settings['height']}:fps={settings['fps']}")
    if settings["color"]["enabled"]:
        color = settings["color"]
        vf.append(f"eq=contrast={float(color['contrast'])}:brightness={float(color['brightness'])}:saturation={float(color['saturation'])}")
    if settings["transition"] == "fade":
        fade = min(settings["transition_seconds"], duration / 4)
        if fade > 0:
            vf += [f"fade=t=in:st=0:d={fade}", f"fade=t=out:st={duration-fade}:d={fade}"]
    if source.get('kind') == 'card':
        fade_in = min(clip.get('card_fade_in', .4), duration / 3)
        fade_out = min(clip.get('card_fade_out', .75), duration / 3)
        if fade_in: vf.append(f"fade=t=in:st=0:d={fade_in}")
        if fade_out: vf.append(f"fade=t=out:st={duration-fade_out}:d={fade_out}")
    args = ["ffmpeg", "-v", "error", "-nostdin", "-y"]
    if is_photo:
        canvas = destination.parent/"photo-canvas.png"
        prepare_canvas(source['path'],settings,clip,canvas)
        args += ["-loop","1","-framerate",str(settings['fps']),"-i",str(canvas)]
    else:
        args += ["-ss",str(clip['start']),"-i",source['path']]
    overlays = []
    if clip.get("caption"):
        if not settings.get("font"):
            raise ValueError("Captions require settings.font with a local supporting font")
        size = int(settings["subtitle_size"])
        if size <= 0:
            raise ValueError("subtitle_size must be positive")
        font = ImageFont.truetype(str(local_file(settings["font"])), size)
        image = Image.new("RGBA", (settings["width"], settings["height"]), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        text = str(clip["caption"])
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=8, align="center")
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        margin = max(12, int(settings["height"] * .05))
        if tw > settings["width"] - margin * 2 or th > settings["height"] - margin * 2:
            raise ValueError("Caption exceeds the frame; use line breaks or reduce subtitle_size")
        x, y = (settings["width"] - tw) / 2, settings["height"] - th - margin
        draw.rounded_rectangle((x-10, y-8, x+tw+10, y+th+8), radius=6, fill=(0, 0, 0, 130))
        draw.multiline_text((x-bbox[0], y-bbox[1]), text, font=font, fill="white", spacing=8, align="center")
        caption = destination.parent / "caption.png"
        image.save(caption)
        overlays.append((caption, None))
    final = []
    if clip.get("card"):
        card = destination.parent / "card.png"
        draw_card(clip["card"], settings, card)
        overlays.append((card, clip["card"]))
        final = black_fades(clip["card"], duration)
    if overlays:
        graph = [f"[0:{source['video_stream']}]" + ",".join(vf) + "[c0]"]
        for index, (image, card) in enumerate(overlays, 1):
            args += ["-loop", "1", "-framerate", str(settings["fps"]), "-i", str(image)]
            label = f"{index}:v"
            if card:
                graph.append(overlay_filter(card, duration, label, f"o{index}"))
                label = f"o{index}"
            graph.append(f"[c{index-1}][{label}]overlay=0:0:shortest=1[c{index}]")
        graph.append(f"[c{len(overlays)}]" + ",".join(final + ["format=yuv420p"]) + "[v]")
        args += ["-filter_complex", ";".join(graph), "-map", "[v]"]
    else:
        args += ["-map", f"0:{source['video_stream']}", "-vf", ",".join(vf)]
    args += ["-an", "-t", str(duration), "-c:v", "libx264", "-preset", settings["preset"],
             "-crf", str(settings["crf"]), "-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709", "-video_track_timescale", "90000", str(destination)]
    run(args)
