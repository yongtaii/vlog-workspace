---
name: vlog-editor
description: Claude Code 전용 일상·여행 Vlog 편집. 로컬 영상과 선택적 사진으로 대표 프레임 검토, HTML 스토리보드, JSON 타임라인, 캐시된 FFmpeg 렌더를 만든다. 첫 편집, 자연어 수정, 실제 장면 위 타이틀·엔딩에 사용한다. Codex 작업물과 분리된 claude lane(analysis/lanes/claude, preview/claude, output/claude)에서만 작업한다.
---

# Natural Daily Vlog Editor · Claude Code

Claude Code가 이 저장소에서 Vlog를 편집할 때 따르는 절차다. Codex는 `skills/vlog-editor/`(Codex Skill)과 기본 작업 공간을 쓴다. Claude는 이 Skill과 **claude lane**을 쓴다. 두 에이전트의 타임라인·수정 이력·미리보기·출력은 섞이지 않는다.

## 작업 공간 분리

| 구분 | Claude (이 Skill) | Codex (건드리지 않음) |
|---|---|---|
| 실행 | `scripts/vlog-claude.sh <명령>` | `scripts/vlog.sh <명령>` |
| 설정 | `config.claude.json` | `config.json` |
| 타임라인·이력·스토리보드 | `analysis/lanes/claude/` | `analysis/timeline.json`, `analysis/revisions/`, `analysis/storyboard.html` |
| 미리보기 | `preview/claude/` | `preview/` 바로 아래 |
| 최종 영상 | `output/claude/vlog.mp4` | `output/vlog.mp4` |
| 타이틀·엔딩 | 실제 컷 위 오버레이 `clip.card` | 별도 카드 화면 `bookends` |

- `scripts/vlog.sh`, `bookends` 명령은 사용하지 않는다. Codex 쪽 파일은 읽기만 한다.
- 공유하는 것: 원본 `input/`, `music/`, 원본 분석 `analysis/analysis.json`과 프레임, 체크섬이 검증된 `analysis/cache/`, 엔진 코드 `src/`. 캐시는 내용 주소 방식이므로 공유해도 서로 덮어쓰지 않는다.
- `analysis/analysis.json`이 있고 input/이 바뀌지 않았다면 analyze를 다시 실행하지 않는다. 입력이 바뀌었으면 사용자에게 알린 뒤 실행한다. 공유 분석이 갱신되기 때문이다.
- 엔진(`src/`)을 바꾸면 Codex 작업에도 영향을 준다. 기존 출력이 바뀌는 변경은 사용자에게 알리고, 테스트를 통과시키고, AGENTS.md의 캐시 규칙을 따른다.

## 공통 계약 (프로젝트의 Codex Skill 참고 문서)

아래 문서는 엔진 동작 계약이라 두 에이전트가 공유한다. 프로젝트 루트 기준 경로로 읽는다.

- 편집 판단: `skills/vlog-editor/references/editing.md`
- 사진 선정·배치: `skills/vlog-editor/references/photos.md`
- 패치 연산·캐시 영향: `skills/vlog-editor/references/revisions.md`

그 문서의 "오프닝·엔딩은 bookends 기본" 같은 Codex 쪽 기본값은 Claude에 적용하지 않는다. 타이틀·엔딩은 아래와 [references/cards.md](references/cards.md)를 따른다.

## 편집 원칙

- 동영상 중심의 자연스러운 흐름: 맥락 → 활동 → 세부 → 마무리. 촬영 시각과 실제 순서를 우선한다.
- 대표 프레임·contact sheet·사진 미리보기는 Read로 직접 열어 본다. 직접 본 것만 "확인했다"고 말한다. 오디오는 들을 수 없으므로 청취 검수를 했다고 하지 않는다.
- 원본에 없는 장소·사건·대화를 지어내지 않는다. 장소명은 프레임에서 읽었거나 사용자가 알려준 경우에만 쓴다.
- 사진은 영상에 없는 중요한 순간을 보완할 때만 hints의 `use:true`와 구체적 reason으로 넣는다. 비율이나 장수 목표를 두지 않는다.

## 타이틀·엔딩 (Claude 방식)

모든 Vlog는 첫 타이틀과 끝 엔딩을 기본으로 가진다. 사용자가 원하지 않으면 생략한다.

- 별도 그래픽 화면을 만들지 않는다. 실제 첫 컷 위에 제목을 얹고 검정에서 열며, 마지막 컷 위에 엔딩 문구를 얹고 화면·소리를 검정으로 닫는다.
- 날짜는 EXIF/creation_time에서 확인한다. 파일 수정일·오늘 날짜를 쓰지 않는다.
- 렌더 후 타이틀 구간(0~4초)과 엔딩 구간(끝 5초)의 프레임을 PNG로 추출해 직접 확인한다. 글자 가독성과 얼굴 겹침을 본다. `-ss <초> -frames:v 1 x.png`를 쓴다. 이 FFmpeg에서는 JPEG 추출이 실패한다.
- 사용한 문구는 결과 보고에 적어 사용자가 바꿀 수 있게 한다.

## 첫 편집

1. `scripts/vlog-claude.sh doctor`. `analysis/analysis.json`이 없거나 입력이 바뀌었을 때만 `scripts/vlog-claude.sh analyze`를 실행한다.
2. `analysis/` 아래 프레임·contact sheet를 보고 장면과 실패 입력을 검토한다.
3. hints는 `analysis/lanes/claude/hints.json`에 쓴다. phase/tags/exclude_ranges/caption/사진 use·reason, 그리고 `@title`/`@ending`을 넣는다. 그다음 `scripts/vlog-claude.sh plan --hints analysis/lanes/claude/hints.json`을 실행한다. @title은 첫 컷, @ending은 마지막 컷에 카드로 붙는다.
4. `analysis/lanes/claude/storyboard.html`로 순서를 검토한다. 고칠 것은 patch로 반영한다.
5. `scripts/vlog-claude.sh preview` → 프레임 확인 → `scripts/vlog-claude.sh render`.

## 자연어 수정

자연어 요청은 Claude가 직접 해석해 patch로 바꾼다. Python CLI가 문장을 이해하는 것이 아니다.

1. `scripts/vlog-claude.sh inspect`로 base_digest와 clip ID를 읽는다.
2. 요청한 변경만 담은 `analysis/lanes/claude/patch.json`을 만든다. 연산 목록은 revisions.md에 있고, `card`·`insert`는 references/cards.md에 있다.
3. `scripts/vlog-claude.sh revise --patch analysis/lanes/claude/patch.json --request '<원문>' --render`를 실행한다.
4. `preview/claude/preview-validation.json`과 `output/claude/full-validation.json`의 cache 이벤트로 실제 재렌더링 범위를 확인한다. 수정 때 plan/analyze를 다시 하지 않는다.

## 결과 보고

`output/claude/vlog.mp4`, `preview/claude/preview.mp4`, `analysis/lanes/claude/timeline.json`, 스토리보드 경로, 재사용/재렌더링 수, 타이틀·엔딩 문구를 알린다. 자동 검증(길이·해상도·FPS·전체 디코딩)과 직접 본 프레임을 구분해서 말한다.
