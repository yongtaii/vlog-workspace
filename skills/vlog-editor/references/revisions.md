# 패치 계약과 캐시 영향

`inspect` 결과의 base_digest는 수정 전 JSON의 정확한 digest다. ID는 화면 순번이 아니라 clips[].id를 쓴다. 다음 예시는 형식 설명이며 실제 ID/digest를 대입한다.

```json
{
  "version": 1,
  "base_digest": "inspect에서 받은 값",
  "operations": [
    {"op": "trim", "clip_id": "실제 ID", "start": 0.0, "end": 3.0},
    {"op": "setting", "key": "music_volume", "value": 0.10}
  ]
}
```

지원 연산:

| op | 필드 | 의미 |
|---|---|---|
| trim | clip_id, start, end | 원본 기준 초로 구간 변경 |
| caption | clip_id, text | 해당 컷 자막 변경/빈 문자열로 제거 |
| audio_gain | clip_id, value | 컷별 원본 오디오 승수, 0은 무음 |
| remove | clip_id | 타임라인에서 제거; 원본 보존 |
| move_before | clip_id, before_id | 다른 컷 앞에 이동; null이면 맨 뒤 |
| setting | key, value | 허용된 렌더링 설정 변경 |
| photo_duration | clip_id, seconds | 사진 표시 길이 변경 |
| photo_style | clip_id, motion, background | 사진 none/zoom/pan, blur/pad |
| ambience | clip_id, value | 사진의 현장음 객체 또는 null로 제거 |
| card | clip_id, value | 타이틀/엔딩 카드 객체 또는 null로 제거. [cards.md](cards.md) |
| insert | clip, before_id | 분석된 source_id의 구간을 새 컷으로 추가; null이면 맨 뒤 |

setting 허용 키: music_volume, source_volume, music, font, subtitle_size, transition, transition_seconds, color, width, height, fps, crf, preset, title_font, title_font_index. 음악/폰트는 절대 로컬 경로 또는 null로 지정한다. 색감은 enabled/contrast/brightness/saturation 전체 객체다. start/end를 바꿔도 원본 전체 길이를 넘을 수 없다. 마지막 컷 제거 등 빈 타임라인은 거부한다. base_digest 불일치/잘못된 연산/범위 오류는 원래 타임라인을 변경하지 않는다.

“컷을 2초 줄여”는 기존 start는 유지하고 end를 2초 앞당긴다. “앞 2초 빼줘”는 start를 2초 뒤로 옮긴다. 부자연스러운 1프레임 이하 컷을 만들지 않는다. “음악 절반”은 현재 music_volume에 0.5를 곱한다. “현장음 크게”는 전역 source_volume 또는 요청한 컷의 audio_gain을 조절한다. 음악이 지정되지 않았으면 볼륨 조절만으로 소리가 생기지 않는다는 사실을 설명한다.

캐시 영향:

| 변경 | 영상 컷 인코딩 | 원본 오디오 컷 | 최종 믹스 |
|---|---|---|---|
| 자막/폰트 | 영향받은 자막 컷 | 재사용 | 재사용 |
| 타이틀/엔딩 문구 | 해당 카드 컷 | 재사용(스타일 변경 시 해당 컷) | 재사용(스타일 변경 시 갱신) |
| 음악/전역 음량 | 재사용 | 재사용 | 갱신 |
| 컷별 현장음 | 재사용 | 해당 컷 | 갱신 |
| 컷 길이/트림 | 해당 컷, 프레임 반올림이 달라진 컷 | 동일 | 갱신 |
| 컷 순서 | 보통 재사용; 프레임 길이 달라지면 갱신 | 동일 | 순서에 맞게 갱신 |
| 전역 색감/해상도/전환 | 해당하는 전체 컷 | 전환 변경이면 갱신 | 입력 변경 시 갱신 |

미리보기 경계에서 잘린 컷은 전체 컷과 길이가 달라 별도 캐시 항목이다. 최종 MP4는 스트림 복사로 재조립하며 전체 디코딩 검증은 다시 수행한다. 이력은 analysis/revisions/*.json에 수정 원문·patch·변경 전 timeline과 변경 후 digest로 저장한다. 복원하려면 해당 before 객체를 timeline.json으로 저장한 뒤 preview/render를 실행한다.
