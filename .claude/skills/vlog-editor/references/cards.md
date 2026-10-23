# 타이틀·엔딩 카드 (Claude 방식)

타이틀/엔딩은 컷에 붙는 `card` 객체다. 새 그래픽 소스가 아니라 실제 영상·사진 컷 위에 텍스트를 얹고 검정 페이드를 준다. 구현은 `src/vlog_editor/cards.py`에 있다.

```json
{"style": "title", "title": "판다 보러 간 날", "subtitle": "2026. 10. 04", "seconds": 3.5}
```

| 필드 | 의미 |
|---|---|
| style | `title`: 컷 시작부터 seconds 동안 글자를 표시하고, 화면·소리를 0.8초 페이드 인한다. `ending`: 컷 끝 seconds 동안 글자를 표시하고, 마지막 1.2초 화면·소리를 페이드 아웃한다 |
| title | 큰 제목. 필수. 길면 `\n`으로 줄을 바꾼다 |
| subtitle | 작은 부제(날짜·장소·한 줄). 선택 |
| seconds | 글자 표시 길이. 생략하면 컷 전체. 컷보다 길면 컷 길이로 맞춘다 |

폰트는 `settings.title_font`(없으면 `settings.font`)와 `title_font_index`를 쓴다. macOS 기본은 `/System/Library/Fonts/AppleSDGothicNeo.ttc`, index 6(Bold)이다. `config.claude.json`에 이미 들어 있다.

## 판단 기준

- 타이틀 컷은 3~5초. 장소·출발 장면이 좋다. 글자가 화면 중앙에 오므로 얼굴이 정중앙에 꽉 찬 컷은 피한다.
- 엔딩 컷은 귀가·잠든 모습·밤 풍경처럼 하루가 닫히는 장면. 4~5초를 확보한다. 사진이면 photo_duration으로 늘린다.
- 제목은 짧게(보통 12자 이내). 장소명은 확인한 경우에만 쓴다. 확인할 수 없으면 날짜를 중심으로 쓴다. 감상 문구는 과장하지 않는다.
- caption과 card를 같은 컷에 함께 쓸 수 있지만, 보통 둘 중 하나만 쓴다.
- Codex의 bookends(kind:card 별도 화면)와 함께 쓰지 않는다. claude lane 타임라인에 bookend 컷이 있으면 제거한다.

## 지정 방법

첫 편집 — `analysis/lanes/claude/hints.json`:

```json
{
  "@title": {"title": "10월의 어느 날", "subtitle": "2026. 10. 23", "seconds": 3.5},
  "@ending": {"title": "오늘의 기록, 끝", "seconds": 3}
}
```

기존 편집 — patch 연산:

```json
{"op": "card", "clip_id": "첫 컷 ID", "value": {"style": "title", "title": "...", "subtitle": "...", "seconds": 3.5}},
{"op": "insert", "clip": {"id": "ending-shot", "source_id": "분석된 소스 ID", "start": 2.0, "end": 7.0, "phase": "closing"}, "before_id": null},
{"op": "card", "clip_id": "ending-shot", "value": {"style": "ending", "title": "..."}}
```

`card`의 value를 null로 하면 카드를 제거한다. 문구만 바꾸면 해당 컷의 영상 인코딩만 다시 하고, 다른 컷은 재사용한다. 스타일을 바꾸면 그 컷의 오디오 페이드와 믹스도 갱신한다.
