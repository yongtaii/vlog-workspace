# 사진 분석·선정·편집 계약

input/photos/는 JPEG/HEIC/HEIF/PNG/WebP/TIFF/BMP를 지원한다. JPEG EXIF 방향을 적용한 파생 이미지만 analysis/에 저장한다. DateTimeOriginal/DateTime과 OffsetTimeOriginal, GPS가 있으면 기록한다. HEIC/HEIF는 로컬 pillow-heif 디코더로 읽는다. RAW는 지원하지 않으므로 별도 변환본이 필요하다. 원본은 변환·회전·삭제하지 않는다.

사진은 분석된 것만으로 자동 삽입되지 않는다. 에이전트(Codex·Claude)가 스토리보드를 보고 중요한 순간을 식별하거나 사용자가 지정한 경우, 다음처럼 포함 이유를 기록한다.

```json
{
  "photos/group.jpg": {
    "use": true,
    "reason": "동영상으로 남기지 못한 가족 기념사진",
    "capture_time": "2026-10-23T15:20:00+09:00",
    "location": "숙소 앞",
    "event": "family-group",
    "display_seconds": 3,
    "motion": "none",
    "background": "blur"
  },
  "videos/arrival.mp4": {
    "capture_time": "2026-10-23T15:10:00+09:00",
    "location": "숙소 앞",
    "event": "arrival"
  }
}
```

use:true와 reason이 있어도 같은 event의 적격 영상 또는 유사 pHash 영상이 있으면 기본적으로 영상이 우선된다. event는 같은 장소 전체가 아니라 같은 순간/행동을 뜻한다. 자동 의미 인식은 없으므로 “기념사진” 여부를 추측하지 않는다. 비슷한 구도라도 별개의 중요한 순간이면 프레임을 확인해 event/중복 판단을 검토한다.

사진 비율/목표 장수는 없다. use가 없으면 영상만으로 편집한다. 승인된 보완 사진에 한해 영상 분량 예산 일부를 사용한다. 자동 계획에서는 사진끼리 연속되는 후보를 제외하고 스토리보드에 사유를 남긴다. 동영상 중심이므로 적격 영상이 하나 이상 필요하다.

스토리 phase → 촬영 시각 → 장소(동일 시각의 보조 정렬) → 원본 내 시각을 반영한다. 시간 정보가 없는 사진에는 내용을 확인해 capture_time/location을 보완한다. EXIF 시간에 시간대가 없으면 config.capture_timezone을 사용한다(기본 +09:00). 다른 여행 시간대라면 설정하거나 시각에 offset을 명시한다. GPS는 로컬 기록만 하며 지오코딩이나 외부 업로드를 하지 않는다.

사진은 기본 3초이며 보통 2~4초를 권한다. 의미에 따라 display_seconds 또는 photo_duration 패치로 조절한다. 사진의 start는 0, end는 표시 시간이며 영상 파일의 길이 제한을 적용하지 않는다. motion:none이 기본이고 zoom/pan은 보호 여백 안에서 약 2%만 움직인다. 전경 전체를 contain 방식으로 배치해 인물/주요 피사체를 자르지 않는다. blur 배경은 장식용 배경만 확장해서 흐리며 전경은 자르지 않는다. pad는 검정 여백이다.

사진 구간의 음악은 전체 믹스에서 끊지 않는다. 앞선 선택 영상에 현장음이 있고 장소가 충돌하지 않으면 최대 끝 2초를 작은 볼륨으로 반복해 분위기를 잇는다. 반복이 부자연스러우면 실제로 들어보고 ambient를 바꾸거나 제거한다. 녹음된 환경음이 없으면 만들어내지 않는다.

타임라인의 ambient는 {source_id: 분석된 영상 ID, start: 원본 초, end: 원본 초, volume: 승수}이다. ambience 패치로 객체를 지정하거나 null로 제거한다. 해당 소스도 SHA-256과 캐시 의존성에 포함된다. 사진 스타일 수정은 해당 영상 컷만, 현장음 수정은 해당 오디오 컷과 믹스만 갱신한다.
