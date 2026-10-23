# 오프닝·엔딩 설정과 재편집

기본 설정:

```json
{
  "bookends": {
    "enabled": true,
    "title": "일상의 기록",
    "ending": "오늘도, 좋은 하루.",
    "opening_seconds": 4,
    "closing_seconds": 4,
    "date_text": null,
    "font": null
  }
}
```

plan/run은 장면을 고른 뒤 add_bookends 단계에서 앞뒤 장면을 생성한다. 순수 장면 선정 함수 make_timeline은 원본 컷만 계획하고 CLI가 생성 장면을 추가한다. 날짜는 선택된 원본의 capture_time을 capture_timezone으로 변환해 얻는다. 여러 날짜면 범위, 없으면 “날짜 미상”이다. 사용자가 제공한 date_text는 우선하지만 에이전트가 날짜를 지어내면 안 된다.

기존 Vlog는 bookends 명령으로 변경한다. 이 명령은 기존 bookend_role:opening/closing 장면만 교체하므로 재실행해도 중복 생성되지 않는다. body 클립의 ID·순서·원본 start/end와 SHA-256은 그대로 유지한다. 변경 전 타임라인은 analysis/revisions/에 남긴다. --no-enabled는 자동 생성한 앞뒤 장면만 제거한다.

오프닝과 엔딩은 kind:card, source kind:card이고 원본 영상·사진과 별개인 파생 이미지다. 제목/날짜는 title_text/date_text에, 역할은 bookend_role에 저장한다. generated-bookend-opening/closing 소스를 참조한다. caption은 별도의 본편 자막이며 이 카드의 제목을 바꾸는 데 사용하지 않는다.

자연어 “첫 제목을 바꿔줘”, “날짜를 고쳐줘”, “엔딩을 짧게”는 기존 timeline을 읽고 bookends 옵션을 변경한다. --title/--ending/--date/--opening-seconds/--closing-seconds/--font로 지정한다. 본편 수정에 쓰는 run/analyze/plan을 다시 실행하지 않는다.

카드는 실제 자료 배경·간결한 글자·짧은 페이드로 구성한다. 한국어 지원 폰트가 필요하고 폰트를 Skill에 임의 재배포하지 않는다. 기본 4초이며 문구 길이에 따라 조정한다. 제목을 바꿔도 다른 카드와 본편 캐시가 유지되는지 검증 JSON의 cache 이벤트로 확인한다.

전체 렌더링 전에는 preview를 다시 만든다. 같은 global 설정과 FPS라면 새 카드 외의 본편은 재사용한다. 미리보기 30초 경계가 이동하므로 그 경계의 일부 컷은 추가 인코딩될 수 있다. 최종 MP4 조립·오디오 믹스·전체 디코딩 검증은 다시 수행한다.
