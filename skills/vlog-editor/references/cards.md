# 기존 컷 위 텍스트 오버레이 계약

기본 오프닝·엔딩은 bookends.md를 따른다. 이 문서는 사용자가 기존 컷 위에 글자를 얹도록 선택한 경우의 호환 기능이다. 별도 앞뒤 장면을 원하지 않으면 bookends를 비활성화한 뒤 사용한다.

이 방식의 타이틀/엔딩은 컷에 붙는 `card` 객체다. 새 그래픽 소스가 아니라 실제 컷 위의 텍스트 오버레이와 검정 페이드다.

```json
{"style": "title", "title": "판다 보러 간 날", "subtitle": "2026. 10. 04", "seconds": 3.5}
```

| 필드 | 의미 |
|---|---|
| style | `title`: 컷 시작부터 seconds 동안 글자 표시, 화면·소리 0.8초 페이드 인. `ending`: 컷 끝 seconds 동안 글자 표시, 마지막 1.2초 화면·소리 페이드 아웃 |
| title | 큰 제목. 필수. 길면 `\n`으로 줄바꿈 |
| subtitle | 작은 부제(날짜·장소·한 줄). 선택 |
| seconds | 글자 표시 길이. 생략 시 컷 전체. 컷보다 길면 컷 길이로 맞춘다 |

## 판단 기준

- 타이틀 컷은 3~5초가 적당하다. 인물 얼굴이 정중앙에 꽉 차거나 흔들림이 심한 컷은 글자가 가리므로 피한다. 넓은 장소·출발 장면이 좋다.
- 엔딩 컷은 귀가·잠든 모습·노을·밤 풍경처럼 하루가 닫히는 장면이 좋다. 4~5초 확보한다. 사진이면 photo_duration으로 늘린다.
- 제목은 짧게(보통 12자 이내) 쓴다. 장소명은 프레임에서 확인했거나 사용자가 알려준 경우에만 쓴다. 감상 문구는 과장하지 않는다. 확인할 수 없으면 날짜 중심으로 쓴다.
- 자막(caption)과 카드는 같은 컷에 함께 쓸 수 있지만 겹쳐 보이므로 보통 둘 중 하나만 쓴다.
- 반투명 어둡게 깔기와 그림자로 가독성을 확보한다. 밝은 하늘·흰 벽에서도 읽히는지 미리보기 프레임으로 확인한다.

## 지정 방법

첫 편집(plan) — hints.json:

```json
{
  "@title": {"title": "10월의 어느 날", "subtitle": "2026. 10. 23", "seconds": 3.5},
  "@ending": {"title": "오늘의 기록, 끝", "seconds": 3}
}
```

`@title`은 계획된 첫 컷, `@ending`은 마지막 컷에 붙는다. config의 title_font(또는 font)가 필요하다.

기존 편집(revise) — patch 연산:

```json
{"op": "setting", "key": "title_font", "value": "/System/Library/Fonts/AppleSDGothicNeo.ttc"},
{"op": "setting", "key": "title_font_index", "value": 6},
{"op": "card", "clip_id": "첫 컷 ID", "value": {"style": "title", "title": "...", "subtitle": "...", "seconds": 3.5}},
{"op": "insert", "clip": {"id": "ending-shot", "source_id": "분석된 소스 ID", "start": 2.0, "end": 7.0, "phase": "closing"}, "before_id": null},
{"op": "card", "clip_id": "ending-shot", "value": {"style": "ending", "title": "..."}}
```

`card`의 value를 null로 하면 카드를 제거한다. 문구 수정은 해당 컷의 영상 인코딩만 다시 하고, 다른 컷과 오디오는 재사용한다(엔딩/타이틀 스타일을 바꾸면 그 컷의 오디오 페이드도 갱신).
