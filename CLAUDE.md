# Claude Code 작업 안내

이 저장소는 Codex와 Claude Code가 함께 쓴다. 원본 보호·검증 같은 공통 규칙은 AGENTS.md에 있으며 아래에서 불러온다. 단, AGENTS.md가 가리키는 `skills/vlog-editor/SKILL.md`는 Codex Skill이다. Claude는 `.claude/skills/vlog-editor/SKILL.md`(`/vlog-editor`)를 따른다.

@AGENTS.md

## Claude 작업 공간 (Codex와 분리)

- 실행은 항상 `scripts/vlog-claude.sh`로 한다. 이 스크립트는 `--lane claude --title-style cards`를 붙여 다음 경로만 쓴다.
  - 타임라인·이력·스토리보드·hints·patch: `analysis/lanes/claude/`
  - 미리보기: `preview/claude/`
  - 최종 영상: `output/claude/vlog.mp4`
  - 설정: `config.claude.json`
- Codex 작업물은 읽기만 한다. 대상: `scripts/vlog.sh`로 만든 `analysis/timeline.json`, `analysis/revisions/`, `analysis/storyboard.html`, `analysis/generated/`, `preview/` 바로 아래 파일, `output/` 바로 아래 파일, `config.json`, `skills/vlog-editor/`.
- 공유 자원: `input/`(읽기 전용), `music/`, `analysis/analysis.json`과 프레임, `analysis/cache/`(체크섬 검증 캐시), `src/` 엔진. 엔진을 고치면 Codex에도 영향을 주므로 사용자에게 알리고 테스트를 통과시킨다.
- 타이틀·엔딩은 실제 컷 위 오버레이(`clip.card`)를 쓴다. Codex의 `bookends` 명령은 쓰지 않는다.
- 프레임은 Read로 직접 열어 확인한다. 오디오는 들을 수 없으므로 청취 검수를 했다고 말하지 않는다.
- `.claude/settings.json`은 공유 권한 설정이다. 개인 설정은 `.claude/settings.local.json`에 둔다.
