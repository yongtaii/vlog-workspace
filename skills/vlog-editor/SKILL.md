---
name: vlog-editor
description: Edit natural daily or travel vlogs from local videos and selectively used photos with representative frames, an offline HTML storyboard, a revisable JSON timeline, and cached FFmpeg renders. Use for first edits or natural-language revisions that preserve original footage and reuse unchanged shots and audio.
---

# Natural Daily Vlog Editor

이 Skill은 편집 판단과 실행 절차를 제공한다. 프로젝트의 AGENTS.md는 해당 저장소의 파일 보호·권한·검증 규칙이다. 둘의 역할을 섞거나 이 Skill을 적용하기 위해 관련 없는 AGENTS.md를 덮어쓰지 않는다. 이 Skill은 Codex용이다. Claude Code는 별도 Skill(`.claude/skills/vlog-editor`)과 분리된 작업 공간(`scripts/vlog-claude.sh`, `analysis/lanes/claude/`, `preview/claude/`, `output/claude/`)을 쓴다. 그 경로는 읽기만 한다.

## 프로젝트 찾기와 재사용

현재 작업 폴더에서 pyproject.toml의 travel-vlog-editor 프로젝트와 scripts/vlog.sh를 찾는다. 없다면 이 Skill 위치 기준 `scripts/bootstrap.py --project <새 폴더> --install`을 실행해 독립 프로젝트를 생성한다. 상대 경로는 현재 디렉터리가 아닌 로드한 Skill 위치에서 해석한다. bootstrap은 이미 있는 파일을 덮어쓰지 않는다. 생성된 프로젝트 README와 AGENTS.md를 읽는다.

영상 원본은 input/videos/, 사진 원본은 input/photos/에 둔다. 다음 작업은 사용자에게 input/videos/와 input/photos/의 자료만 교체하도록 안내하고 같은 run 명령을 사용한다. 에이전트가 이전 원본을 삭제하거나 교체하지 않는다. 선택 음악은 music/에 두어 작업 간 유지한다. 폰트는 별도 로컬 경로로 지정한다. 본편 자막·배경음악·색보정은 선택 사항이며, 날짜가 있는 오프닝과 짧은 엔딩은 기본으로 생성한다.

## 편집 판단

[자연스러운 일상 Vlog 기준](references/editing.md)을 읽는다. 이미지는 중요한 장면을 찾는 단서이며 선명도 순위가 최종 스토리를 대신하지 않는다. 직접 확인한 프레임을 바탕으로 맥락→활동→세부 장면→마무리 흐름을 만든다. 현장음과 실제 시간 흐름을 우선하며 원본에 없는 장소·사건·대화를 지어내지 않는다. 샘플 기반 자동 분석의 한계를 인정한다.

## 오프닝·엔딩 기본 지침

앞으로 만드는 Vlog에는 별도 요청이 없어도 날짜가 있는 첫 타이틀 장면과 마지막 엔딩 장면을 기본으로 포함한다. 사용자가 제외해 달라고 하면 해당 요청을 우선한다.

- 오프닝은 기본 약 4초. 실제 장면에 맞는 짧은 제목과 촬영 날짜를 읽기 쉽게 표시한다. 기본 제목은 “일상의 기록”이며 내용을 직접 검토한 뒤 적절하게 바꾼다.
- 날짜는 원본 영상/사진의 촬영 메타데이터와 작업 시간대에서 얻는다. 사용자 지정 날짜가 있으면 우선한다. 여러 날짜면 범위를 표시한다. 파일 수정일·오늘 날짜를 촬영일로 대신 쓰지 않는다. 정보가 없으면 임시로 “날짜 미상”을 표시하고 날짜를 확인한다.
- 엔딩은 기본 약 4초. 마지막 장면과 이어지는 배경과 짧은 마무리 문구를 사용한다. 기본 문구는 “오늘도, 좋은 하루.”다. 구독/좋아요 문구는 요청이 있을 때만 넣는다.
- 실제 자료를 배경으로 간결한 글자와 짧은 페이드를 사용한다. 인물·주요 피사체와 겹치지 않게 배치하고 한국어 폰트와 16:9 여백을 확인한다.
- 새 plan/run은 자동 생성한다. 기존 편집에 추가하거나 문구·날짜를 바꿀 때는 `scripts/vlog.sh bookends --title '<제목>' --ending '<문구>'`를 사용한다. 원본과 본편 컷은 다시 계획하지 않는다.
- 수정 뒤 preview를 검증하고, 전체 렌더링이 승인된 경우 render한다. bookends 명령 자체는 렌더링하지 않는다. 삭제는 `bookends --no-enabled`다.
- [오프닝·엔딩 설정](references/bookends.md)을 참고한다. 장면은 JSON 타임라인의 kind:card이며 실제 사진 사용 비율에 포함하지 않는다.

## 사진 활용 지침

- 동영상을 중심으로 자연스러운 일상 Vlog를 제작한다.
- 사진은 스토리를 보완할 때만 선택적으로 사용한다.
- 사진 사용 비율을 미리 정하지 않는다.
- 좋은 동영상이 충분한 경우 사진을 억지로 넣지 않는다.
- 동영상에 없는 중요한 순간이나 기념사진을 우선한다.
- 촬영 시간과 장소를 기준으로 사진과 동영상을 배치한다.
- 동일한 장면의 사진과 동영상이 있다면 기본적으로 동영상을 우선한다.
- 사진은 기본적으로 2~4초 정도 표시하되 장면의 의미에 따라 조정한다.
- 필요한 경우에만 미세한 줌 또는 패닝을 적용한다.
- 16:9 화면에 맞추되 인물이나 주요 피사체를 자르지 않는다.
- 세로 사진은 여백이나 흐린 배경을 활용한다.
- 사진이 너무 연속적으로 등장하지 않도록 한다.
- 사진 구간에도 음악과 환경음의 흐름을 자연스럽게 유지한다.
- 원본 사진은 수정하거나 삭제하지 않는다.

사진 스토리보드를 직접 확인한 뒤, 보완 의미가 있는 사진에만 hints의 use:true와 구체적 reason을 기록한다. 사진 부족분/사용 비율을 목표로 지정하지 않는다. [사진 분석·선정·편집 계약](references/photos.md)을 읽어 촬영 시각·장소·event와 중복 여부를 판단한다.

## 기존 컷 위의 글자 오버레이(선택)

별도 오프닝·엔딩 대신 기존 컷 위에 글자를 얹고 싶다는 요청에는 [오버레이 카드 계약](references/cards.md)의 clip.card를 사용할 수 있다. 기본은 위의 bookends 방식이며 두 방식을 겹쳐 같은 제목을 두 번 표시하지 않는다. 사용자 요청에 따라 bookends를 비활성화하고 기존 영상/사진 컷 위에 카드 글자와 페이드를 적용할 수 있다. 기존 코드의 card/insert 연산은 호환성을 위해 유지한다.

## 첫 편집

1. `scripts/vlog.sh doctor`, `scripts/vlog.sh analyze`를 실행한다.
2. analysis/storyboard.html, 영상 대표 프레임·contact sheet와 사진 미리보기를 열어 실제 장면과 실패 입력을 검토한다.
3. 필요할 때만 hints.json에 phase/tags/priority/exclude_ranges/caption을 기록하고 `scripts/vlog.sh plan --hints hints.json`을 실행한다. 힌트가 필요 없으면 plan만 실행한다. HTML 스토리보드에서 선택 순서와 제외 사유를 검토한다.
4. 자동 생성된 오프닝의 제목·촬영 날짜와 엔딩 문구를 검토한다. 긴 정지 구간과 불필요한 반복을 줄이되 공간·행동을 이해할 여유를 둔다. 타임라인 clips와 settings를 수정하고 `scripts/vlog.sh storyboard`로 검토 화면을 갱신한다.
5. `scripts/vlog.sh preview` 후 화면·컷·자막·소리를 가능한 범위에서 직접 검토하고 `scripts/vlog.sh render`를 실행한다. 자동 검증과 직접 검토 여부를 구분해서 보고한다.

## 자연어 수정

사용자의 “두 번째 컷 2초 줄이고 음악을 낮춰줘”, “마지막 장면을 앞으로”, “자막만 바꿔줘”를 현재 에이전트(Codex 또는 Claude Code)가 해석한다. Python CLI가 자유 문장을 이해한다고 주장하지 않는다. 의미 해석은 현재 에이전트가 수행하며 추가 유료 API나 외부 업로드를 호출하지 않는다.

1. `scripts/vlog.sh inspect`로 최신 base_digest, clips ID/순서/시간/settings를 읽는다. 위치 표현을 안정적인 ID로 변환한다. 같은 태그의 장면이 여럿이면 스토리보드로 식별한다. 어느 장면인지 정할 수 없는 경우에만 확인한다.
2. [패치 계약과 캐시 영향](references/revisions.md)에 따라 요청한 변경만 담은 analysis/patch.json을 만든다. 최상위 설정 전체를 불필요하게 재작성하지 않는다. 요청 문장을 --request에 원문으로 남긴다.
3. `scripts/vlog.sh revise --patch analysis/patch.json --request '<원문>' --render`를 실행한다. 이 명령은 수정 이력·스토리보드 갱신→preview/ 미리보기 검증→output/ 전체 증분 렌더링을 수행한다.
4. preview/preview-validation.json과 output/full-validation.json의 cache 이벤트에서 실제 재렌더링 범위를 확인한다. “필요한 부분만”은 컷/사운드 캐시 단위이며 최종 MP4 재조립과 검증은 필요하다. 수정 후 run/analyze/plan을 반복하지 않는다.

## 결과 보고

HTML 스토리보드, preview.mp4, vlog.mp4, timeline.json 경로와 재사용/재렌더링 수를 제공한다. 실제로 수행한 검증과 직접 본 프레임/청취 여부만 말한다. input/에 실제 영상이 없으면 합성 검증은 별도 analysis/ 폴더에 두고 실제 일상 Vlog와 구별한다.
