# Natural Daily Vlog Editor · 영상 + 사진

Python/OpenCV/FFmpeg로 동영상 중심의 자연스러운 일상·여행 Vlog를 만든다. 사진은 스토리 보완용으로 선택하며 비율이나 장수 목표를 정하지 않는다. 원본 영상·사진·음악·폰트는 읽기만 한다. 외부 업로드나 유료 API를 사용하지 않는다.

## 작업 폴더

```text
vlog-workspace/
├── AGENTS.md         # 공통 작업 규칙 (Codex·Claude)
├── CLAUDE.md         # Claude Code 진입점, @AGENTS.md 불러옴
├── config.claude.json # Claude lane 설정
├── .claude/
│   ├── settings.json # Claude 권한 (input/·music/·Codex 타임라인 편집 금지)
│   └── skills/vlog-editor/  # Claude 전용 Skill
├── .agents/skills/vlog-editor -> ../../skills/vlog-editor
├── input/
│   ├── videos/       # 원본 동영상
│   └── photos/       # 원본 사진
├── music/            # 선택 배경음악
├── skills/
│   └── vlog-editor/
│       ├── SKILL.md
│       ├── references/
│       └── scripts/
├── analysis/          # 분석 JSON·대표 프레임·HTML·타임라인·캐시·수정 이력
├── preview/           # 최대 30초 미리보기와 검증 보고서
└── output/
    └── vlog.mp4
```

실행 코드인 src/, scripts/, tests/, pyproject.toml, config.json도 프로젝트에 포함된다. `.agents/skills/vlog-editor`는 Codex Skill `skills/vlog-editor`를 가리키는 symlink다. Claude Code는 별도 Skill `.claude/skills/vlog-editor`를 쓴다.

### Codex / Claude 작업 분리

| | Codex | Claude Code |
|---|---|---|
| 실행 | `scripts/vlog.sh` | `scripts/vlog-claude.sh` (`--lane claude --title-style cards`) |
| 설정 | config.json | config.claude.json |
| 타임라인·이력·스토리보드 | analysis/ 바로 아래 | analysis/lanes/claude/ |
| 미리보기 / 최종 | preview/, output/vlog.mp4 | preview/claude/, output/claude/vlog.mp4 |
| 타이틀·엔딩 | bookends (별도 카드 화면) | clip.card (실제 컷 위 오버레이) |

원본 분석(analysis/analysis.json, 프레임), 체크섬 검증 캐시(analysis/cache/), 엔진 코드(src/)는 공유한다. 다른 이름이 필요하면 `--lane <이름>`으로 별도 작업 공간을 만들 수 있다. 작업물은 위 analysis/preview/output에 분리한다.

AGENTS.md는 파일 보호·권한·검증 등 프로젝트 작업 규칙이다. CLAUDE.md는 `@AGENTS.md`로 같은 규칙을 불러오고 Claude 전용 메모만 덧붙이므로 규칙 변경은 AGENTS.md에서 한다. SKILL.md는 실제 편집 판단·사진 활용·자연어 수정 절차다. 사진 세부 계약은 [photos.md](skills/vlog-editor/references/photos.md), 수정 계약은 [revisions.md](skills/vlog-editor/references/revisions.md)에 있다.

## 설치 및 실행

Python 3.11 이상과 PATH의 FFmpeg/ffprobe가 필요하다. FFmpeg는 libx264/AAC/overlay 필터를 지원해야 한다.

```bash
cd vlog-workspace
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
scripts/vlog.sh doctor
```

input/videos/에 동영상을, input/photos/에 선택 사진을 둔다. 다음 작업에서는 사용자가 두 폴더의 입력 자료만 교체하면 된다. 코드·Skill·설정을 매번 바꿀 필요는 없다. 프로그램은 이전 원본을 자동 교체하거나 삭제하지 않는다. 기존의 input/ 직하 영상도 호환을 위해 검색한다.

```bash
# 기본 실행: 사진도 분석하지만 이유가 지정되지 않은 사진은 삽입하지 않는다.
scripts/vlog.sh run

# 스토리를 검토하면서 편집
scripts/vlog.sh analyze
# analysis/storyboard.html과 대표 프레임·사진을 열어 검토
# hints.example.json을 참고해 실제 입력의 상대 경로로 hints.json 작성
scripts/vlog.sh plan --hints hints.json
scripts/vlog.sh preview
scripts/vlog.sh render
```

전체 렌더링은 현재 타임라인·원본·음악·폰트에 맞는 미리보기가 자동 검증을 통과해야 실행된다. run은 분석/계획을 새로 생성하므로 자연어 수정 뒤에는 run 대신 revise 또는 preview/render를 사용한다.

target_seconds:null은 총길이 무제한이며 적격 장면의 흐름으로 분량을 정한다. 숫자를 지정하면 해당 초를 상한으로 사용한다. 현재 출력은 총길이 무제한, 1920×1080 16:9, 30fps다. 사용 가능한 영상이 부족하면 억지로 늘리지 않는다. 사진만으로 슬라이드쇼를 자동 제작하지 않으며 적격 영상이 하나 이상 필요하다.

## 사진 활용

- 동영상이 중심이다. 좋은 영상이 충분하면 사진을 억지로 추가하지 않는다.
- 동영상에 없는 중요한 순간이나 기념사진에 한해 use:true와 구체적인 reason을 기록한다. 고정 사용 비율은 없다.
- 같은 event 또는 유사한 영상 프레임이 있으면 영상을 우선한다. event는 같은 장소 전체가 아니라 같은 순간·행동을 식별한다.
- 촬영 시각과 장소를 기준으로 사진과 영상을 배치한다. 스토리 phase를 먼저 적용한 뒤 촬영 시각을 따른다. 영상 안의 컷 시작 시간도 반영한다.
- 기본 사진 표시는 3초이며 보통 2~4초를 권한다. 의미에 따라 조절할 수 있다.
- 기본은 정지 사진이다. 필요한 경우만 미세한 zoom/pan을 선택한다.
- 16:9 안에 전경 전체를 contain으로 배치한다. 세로 사진은 흐린 배경(blur) 또는 검정 여백(pad)을 선택한다. 전경을 자르지 않는다. 움직임도 보호 여백 안에서 약 2%만 적용한다.
- 자동 계획은 연속 사진 후보를 제외한다. 검토 화면에 제외 사유를 남긴다.
- 음악은 사진 구간에도 이어진다. 앞선 영상에 현장음이 있고 장소가 충돌하지 않으면 끝 최대 2초를 작은 볼륨으로 반복해 연결한다. 반복이 부자연스러우면 들어보고 변경/제거한다. 없는 환경음을 만들어내지 않는다.
- 원본 사진의 방향·픽셀·EXIF를 바꾸거나 삭제하지 않는다. 파생 이미지에만 회전과 배치를 적용한다.

```json
{
  "photos/memory.jpg": {
    "use": true,
    "reason": "동영상으로 남기지 못한 가족 기념사진",
    "capture_time": "2026-10-23T09:30:00+09:00",
    "location": "숙소 앞",
    "event": "family-group",
    "display_seconds": 3,
    "motion": "none",
    "background": "blur"
  }
}
```

사진은 JPEG/HEIC/HEIF/PNG/WebP/TIFF/BMP를 지원한다. JPEG EXIF의 방향·촬영 시각·시간대·GPS가 있으면 기록한다. HEIC/HEIF는 로컬 pillow-heif로 읽으며 원본은 변환하지 않는다. RAW는 별도 변환본이 필요하다. 자동 변환이나 외부 업로드는 하지 않는다. GPS는 로컬 기록만 하며 지오코딩하지 않는다.

촬영 시각/장소가 없으면 Codex가 실제 자료를 보고 hints를 보완한다. 시간대 없는 EXIF는 config.capture_timezone을 적용한다(기본 +09:00). 해외 여행은 적절한 시간대로 바꾸거나 capture_time에 offset을 명시한다. 장소는 동일 시각의 보조 정렬에도 사용하며 서로 다른 날의 같은 장소를 임의로 합치지 않는다.

## 분석과 모듈

| 모듈 | 역할 |
|---|---|
| analyze.py, photos.py | ffprobe 동영상 정보, 프레임/흔들림/초점/장면 분석, 사진 EXIF/파생 이미지 |
| selection.py, photos.py | 영상 품질·중복 제외, 다양성, 이유가 있는 보완 사진 선택 |
| story.py, planner.py | 촬영 시각·장소·phase 정렬, 사진 연속 억제, 타임라인 생성 |
| cut.py | 영상 트림, 자막/색감/전환, 사진 배치와 선택 모션 |
| sound.py | 원본 오디오, 사진 현장음 연결, 배경음악과 볼륨 |
| render.py, cache.py, validation.py | 영상/오디오 독립 캐시, 조립과 검증 |
| storyboard.py, revision.py | 로컬 HTML 검토, 요청 기반 패치와 이력 |

동영상은 길이·해상도·회전·방향·FPS·촬영 시각·오디오 스트림과 raw ffprobe 결과를 저장한다. 일정 간격 프레임의 선명도/노출/pHash, 히스토그램 변화, 가까운 프레임의 optical flow로 흐림·흔들림·중복 후보를 제외한다. 품질 점수만이 아니라 소스·장면·스토리 단계의 다양성도 선택에 반영한다.

분석은 샘플 기반이며 의미 인식 모델이 아니다. 샘플 사이의 흔들림/초점 문제, 같은 사건의 다른 구도 등은 놓칠 수 있다. HTML 스토리보드에서 선택 순서·컷 ID·대표 프레임·사진·원본 링크·태그·근거·제외 사유를 검토한다. `scripts/vlog.sh storyboard`로 수동 JSON 편집 후 갱신할 수 있다.

## 날짜가 있는 첫 타이틀과 마지막 엔딩

새 plan/run에는 기본 4초 오프닝과 4초 엔딩이 자동으로 추가됩니다. 실제 자료를 배경으로 간결한 제목·촬영 날짜와 짧은 마무리 문구를 표시하고 부드럽게 페이드합니다. 본편 컷/원본은 바꾸지 않습니다.

```bash
# 기존 편집의 앞뒤만 추가/수정: 본편을 재계획하지 않음
scripts/vlog.sh bookends --title '아이와 함께한 하루' --ending '오늘도, 좋은 하루.'
scripts/vlog.sh preview
scripts/vlog.sh render
# 날짜를 명시하거나 장면 길이 조절
scripts/vlog.sh bookends --date '2026.10.04' --opening-seconds 4 --closing-seconds 4
# 사용자가 앞뒤 장면을 제외하고 싶은 경우
scripts/vlog.sh bookends --no-enabled
```

설정은 config.json 또는 timeline.settings.bookends의 enabled/title/ending/opening_seconds/closing_seconds/date_text/font입니다. date_text:null이면 원본 촬영 시각과 capture_timezone으로 날짜를 계산하며 여러 날짜는 범위를 표시합니다. 날짜가 없으면 “날짜 미상”으로 두고 실제 날짜를 확인합니다. 오늘 날짜나 파일 수정일을 사용하지 않습니다. font:null이면 지원되는 한국어 시스템 폰트를 찾으며 없으면 로컬 폰트를 지정해야 합니다.

생성 PNG는 analysis/generated/bookends/에 저장되고 타임라인의 kind:card 장면으로 관리합니다. 글자와 날짜를 바꾸면 해당 장면만 새로 만들며 본편의 영상·오디오 캐시는 유지합니다. 실제 사진 선택 수에는 타이틀/엔딩을 포함하지 않습니다. 자세한 계약은 [bookends.md](skills/vlog-editor/references/bookends.md)에 있습니다.

## 음악·자막·전환

config.json에서 music을 `music/bgm.wav` 같은 로컬 경로로 지정한다. 음악을 자동으로 임의 선택하지 않는다. 자막은 선택 폰트를 지정하고 컷별 caption을 설정한다. 상대 음악/폰트 경로는 config 파일 폴더 기준이며 타임라인에는 절대 경로로 고정한다.

전환 기본은 cut이다. fade는 짧은 dip-to-black이며 겹침 crossfade가 아니다. 색감은 선택 EQ이고 HLG/BT.2020 영상은 1000nit 기준 SDR 표시 변환을 지원한다. PQ와 Dolby Vision 동적 메타데이터의 전체 재현, 카메라 간 자동 색 매칭은 포함하지 않는다. 자막은 Pillow PNG 합성으로 한국어와 문장부호를 지원하며 drawtext 빌드 옵션에 의존하지 않는다.

오디오는 48kHz 스테레오로 맞춘다. 음악은 반복·시작/끝 페이드와 limiter를 적용한다. LUFS 정규화, 대사 인식/ducking, 음악 박자 편집은 포함하지 않는다.

## 자연어 수정과 부분 렌더링

Codex 또는 Claude Code에 “첫 사진을 4초로”, “사진의 줌을 없애줘”, “배경음악을 낮춰줘”처럼 요청한다. 에이전트가 최신 타임라인과 스토리보드로 대상을 확인한 뒤 패치로 변환한다. Python CLI가 자유 문장 자체를 이해한다고 주장하지 않는다. 추가 유료 API를 호출하지 않는다.

```bash
scripts/vlog.sh inspect
# 에이전트가 정확한 base_digest와 clip_id로 analysis/patch.json 작성
scripts/vlog.sh revise --patch analysis/patch.json --request '첫 사진을 4초로 바꿔줘' --render
```

연산: trim, caption, audio_gain, remove, move_before, setting, photo_duration, photo_style, ambience, card, insert. 기본 앞뒤 장면은 bookends로 관리하며 기존 컷 위 오버레이는 선택적으로 card 연산 또는 hints의 `@title`/`@ending`으로 지정한다([cards.md](skills/vlog-editor/references/cards.md)). 사진 start는 0, end는 표시 길이다. ambience 값은 분석된 영상 source_id/start/end/volume 객체 또는 null이다.

클립 순서/start/end/caption/settings는 analysis/timeline.json에서 직접 수정할 수도 있다. timeline_start와 총 duration은 자동으로 다시 계산한다. 원본 참조와 SHA-256을 유지해야 한다. 원본이 변경되면 재분석을 요구한다.

영상/오디오는 analysis/cache/에 독립 저장한다. 사진 모션/자막 변경은 해당 영상 컷만, 사진 현장음 변경은 해당 오디오와 믹스만, 음악/전역 음량 변경은 믹스만 재처리한다. 컷 길이와 FPS 반올림, 미리보기 경계가 달라지면 일부 추가 컷을 처리할 수 있다. 마지막 MP4 조립은 스트림 복사로 수행하고 전체 디코딩 검증은 다시 한다.

수정 전 digest가 다르거나 패치가 잘못되면 기존 타임라인을 유지한다. analysis/revisions/에 원문·patch·변경 전 타임라인을 보존한다. 캐시는 재사용 전 체크섬을 확인하며 자동 삭제하지 않는다.

## Skill 재사용과 검증

```bash
# 새 배포 번들 생성 (기존 설치 Skill을 임의로 덮어쓰지 않음)
.venv/bin/python scripts/package_skill.py
# 설치된 Skill에서 새 독립 작업 폴더 생성
python3 ~/.codex/skills/vlog-editor/scripts/bootstrap.py --project ~/Videos/vlog-workspace --install
# 사용자 전역 설치: --agent codex(기본) | claude | all
.venv/bin/python scripts/package_skill.py --install --agent claude
```

Codex CLI에서 `$vlog-editor`로 호출한다. [OpenAI 공식 Skill 문서](https://learn.chatgpt.com/docs/build-skills)를 참고한다. 프로젝트 원본 Skill은 skills/vlog-editor/이며 사용자 설치 번들은 ~/.codex/skills/vlog-editor, 검색용 symlink는 ~/.agents/skills/vlog-editor다.

Claude Code에서는 `/vlog-editor`로 호출하거나 요청 내용으로 자동 선택된다. 이 작업 폴더에서는 `.claude/skills/vlog-editor`(Claude 전용)로 바로 인식된다. 전역 설치(`--agent claude`)는 이 Claude Skill을 ~/.claude/skills/vlog-editor에 복사한다. bootstrap으로 만든 새 프로젝트에도 CLAUDE.md, .claude/, config.claude.json, scripts/vlog-claude.sh가 함께 생성된다.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/smoke_test.py --directory analysis/video-check
.venv/bin/python scripts/test_incremental.py --project analysis/video-check
.venv/bin/python scripts/test_photos.py --video-fixtures analysis/video-check --directory analysis/photo-check
```

합성 통합 시험은 전용 새 폴더만 사용한다. 실제 input/에 샘플을 넣지 않는다. 동영상 30초 미리보기/36초 전체, 혼합 30초 미리보기/42초 전체, 사진 스타일 수정의 캐시 재사용, 사진 현장음, 원본 SHA-256 보존을 확인한다.

검증 JSON은 길이·해상도·FPS·H.264·오디오 존재와 전체 디코딩을 확인한다. `visual_review: pending_human_review`는 미적 품질이나 청취 완료를 뜻하지 않는다. 첫 30초뿐 아니라 최종 영상의 뒤쪽 사진/자막도 검토해야 한다.
