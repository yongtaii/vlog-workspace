"""Offline HTML review, with escaped user text and relative local media links."""
from html import escape
import os
from pathlib import Path
from urllib.parse import quote

from .common import protect_output


def write_storyboard(analysis, timeline, destination):
    destination = protect_output(destination, analysis["input_dir"], [v["path"] for v in analysis["videos"]+analysis.get("photos",[])])
    destination.parent.mkdir(parents=True, exist_ok=True)
    def href(path):
        return quote(os.path.relpath(path, destination.parent), safe="/")
    def e(value):
        return escape(str(value), quote=True)
    cards = []
    videos = {v["id"]: v for v in analysis["videos"]+analysis.get("photos",[])}
    clips = timeline["clips"] if timeline else []
    for index, clip in enumerate(clips):
        video = videos.get(clip["source_id"])
        if video is None and clip.get('kind') == 'card':
            video = {'samples': [{'time': 0., 'frame': clip['source']}]}
        if video is None:
            raise ValueError(f"No analyzed source for storyboard clip: {clip['id']}")
        sample = min(video["samples"], key=lambda s: abs(s["time"] - (clip["start"] + clip["end"]) / 2))
        cards.append(f'''<article><img loading="lazy" src="{href(sample['frame'])}" alt="대표 프레임">
<h3>{index+1}. [{e(clip.get('kind','video'))}] {e(Path(clip['source']).name)}</h3><code>{e(clip['id'])}</code>
<p>타임라인 {clip['timeline_start']:.2f}s · 원본 {clip['start']:.2f}–{clip['end']:.2f}s · {e(clip['phase'])}</p>
<p>{e(clip.get('title_text',clip.get('caption','')))} {e(clip.get('date_text',''))}</p>{f"<p><strong>{'타이틀' if clip['card']['style']=='title' else '엔딩'}</strong>: {e(clip['card']['title'])} · {e(clip['card'].get('subtitle',''))}</p>" if clip.get('card') else ''}<p>{e(', '.join(clip.get('tags',[])))}</p>
<a href="{href(clip['source'])}">원본 열기</a>
<details><summary>선정 근거</summary><pre>{e(clip.get('metrics',{}))}\n{e(clip.get('reason',[]))}</pre></details></article>''')
    for video in analysis["videos"]+analysis.get("photos",[]):
        sheets = ''.join(f'<a href="{href(p)}"><img loading="lazy" src="{href(p)}" alt="contact sheet"></a>' for p in video["contact_sheets"])
        cards.append(f'<article><h3>소스: {e(video["relative_path"])}</h3><p>{video["duration"]:.2f}s · {e(video["orientation"])} · 오디오 {len(video["audio"])}</p>{sheets}</article>')
    rejected = ''.join(f'<li><code>{e(c["id"])}</code>: {e(", ".join(c["reason"]))}</li>' for c in (timeline or {}).get('rejected',[]))
    errors = ''.join(f'<li>{e(error)}</li>' for error in analysis.get('errors',[]))
    page = '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Natural Daily Vlog — 스토리보드</title><style>
body{font:16px system-ui;background:#131a21;color:#e6edf3;max-width:1320px;margin:auto;padding:28px}a{color:#85c7ff}code,pre{overflow-wrap:anywhere;white-space:pre-wrap}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}article{padding:18px;background:#202b36;border-radius:12px}img{width:100%;max-height:420px;object-fit:contain}h1{font-size:28px}</style>
<h1>Natural Daily Vlog · 스토리보드</h1><p>로컬 분석 및 편집 순서 검토. 대표 프레임은 샘플이므로 실제 컷 경계와 다를 수 있습니다.</p>'''
    if timeline:
        page += f'<p>총 {timeline["duration"]:.2f}초 · {len(clips)}개 컷</p>'
    page += '<main>'+''.join(cards)+'</main><details><summary>제외 후보</summary><ul>'+rejected+'</ul></details><ul>'+errors+'</ul></html>'
    staged = destination.with_suffix('.html.tmp')
    staged.write_text(page, encoding='utf-8')
    staged.replace(destination)
    return destination
