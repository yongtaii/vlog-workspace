"""Source audio per shot, ambience gain and independent background music mixing."""
from .cards import audio_fades
from .common import local_file, run


def audio_key(clip, source, settings, duration, ambient_source=None):
    key = {"source": source["fingerprint"], "streams": source["audio"], "start": clip["start"],
           "duration": duration, "ambient": clip.get("ambient"),
           "ambient_fingerprint": ambient_source["fingerprint"] if ambient_source else None,
           "gain": clip.get("source_volume", 1.0), "transition": settings["transition"],
           "transition_seconds": settings["transition_seconds"]}
    if clip.get("card"):
        key["card"] = clip["card"]["style"]
    if source.get("kind") == "card":
        key["card_audio_version"] = 1
    return key


def render_audio(clip, source, settings, duration, destination, ambient_source=None):
    args = ["ffmpeg", "-v", "error", "-nostdin", "-y"]
    ambient = clip.get('ambient')
    if ambient_source and ambient:
        args += ["-ss",str(ambient['start']),"-i",ambient_source['path'],"-map",f"0:{ambient_source['audio'][0]['index']}"]
    elif source["audio"]:
        args += ["-ss", str(clip["start"]), "-i", source["path"], "-map", f"0:{source['audio'][0]['index']}"]
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    af = ["aresample=48000:async=1:first_pts=0", "aformat=channel_layouts=stereo",
          "asetpts=PTS-STARTPTS", "apad", f"atrim=duration={duration}", f"volume={clip.get('source_volume',1.)}"]
    if ambient_source and ambient:
        length = ambient['end']-ambient['start']
        # Trim first, then repeat just the actual neighbouring ambience segment.
        af = ["aresample=48000", "aformat=channel_layouts=stereo",f"atrim=duration={length}",
              "asetpts=PTS-STARTPTS",f"aloop=loop=-1:size={round(length*48000)}",
              f"atrim=duration={duration}",f"volume={ambient.get('volume',1.)*clip.get('source_volume',1.)}",
              "afade=t=in:d=0.12",f"afade=t=out:st={max(0,duration-.12)}:d=0.12"]
    if settings["transition"] == "fade" and settings["transition_seconds"] > 0:
        fade = min(settings["transition_seconds"], duration / 4)
        af += [f"afade=t=in:d={fade}", f"afade=t=out:st={duration-fade}:d={fade}"]
    if clip.get("card"):
        af += audio_fades(clip["card"], duration)
    if source.get('kind') == 'card':
        fade = min(1., duration / 3)
        af += [f"afade=t=in:d={fade}", f"afade=t=out:st={duration-fade}:d={fade}"]
    args += ["-vn", "-af", ",".join(af), "-t", str(duration), "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(destination)]
    run(args)


def mix_audio(joined, settings, duration, destination):
    args = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(joined)]
    graph = f"[0:a]volume={settings['source_volume']}[original];"
    if settings.get("music"):
        args += ["-stream_loop", "-1", "-i", str(local_file(settings["music"]))]
        graph += (f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume={settings['music_volume']},"
                  f"afade=t=in:d=1,afade=t=out:st={max(0,duration-2)}:d={min(2,duration)}[music];"
                  "[original][music]amix=inputs=2:duration=first:normalize=0[mixed];[mixed]")
    else:
        graph += "[original]"
    graph += "alimiter=limit=0.95:latency=1[a]"
    args += ["-filter_complex", graph, "-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", str(duration), str(destination)]
    run(args)
