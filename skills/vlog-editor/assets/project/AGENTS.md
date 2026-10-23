# 프로젝트 작업 규칙

이 파일은 이 저장소에서 작업하는 에이전트(Codex·Claude Code 공통)의 권한·파일 경계·검증 규칙이다. 편집 스타일, 장면 판단, 자연어 수정 실행 방법은 `skills/vlog-editor/SKILL.md`를 읽는다. AGENTS.md를 Skill 대신 사용하지 않는다.

- input/videos/ 영상·input/photos/ 사진과 연결된 실제 원본, 음악, 폰트는 읽기만 한다. 수정·삭제·덮어쓰기·자동 정리하지 않는다. symlink도 실제 경로를 검사한다.
- 파생 파일은 analysis/, preview/, output/에 둔다. 외부 업로드·유료 API는 실행 전에 사용자 승인을 받는다. 기본 구현은 로컬 전용이다.
- 새 입력 작업은 run, 기존 편집 수정은 revise 또는 preview/render로 수행한다. 자연어 수정에 run을 사용해 기존 결정을 재계획하지 않는다.
- 미리보기는 최대 30초로 먼저 생성하고 전체 디코딩·길이·해상도·FPS·오디오 검증 후 전체 렌더링한다. 현재 타임라인/원본/음악/폰트에 대응하는 검증 gate를 우회하지 않는다.
- 분석 실패·샘플 기반 한계·합성 자료 여부를 보고한다. 자동 검증을 미적 검수나 청취 완료로 표현하지 않는다.
- 캐시 키는 출력에 영향을 주는 소스/효과/폰트/오디오 설정을 반영한다. 기존 장면의 출력이 바뀌는 렌더링 변경 시 cache.ENGINE_VERSION을 올린다. 새 장면 종류만 추가하면 해당 종류 전용 캐시 버전을 넣어 기존 컷을 재사용할 수 있다. 캐시 사용 전 체크섬을 검사한다.
- 테스트: `.venv/bin/python -m pytest -q`. 통합: `.venv/bin/python scripts/smoke_test.py --directory analysis/<새 폴더>`. 증분 회귀: `.venv/bin/python scripts/test_incremental.py --project analysis/<통합 폴더>`.
- 합성 검증 영상은 analysis/에 격리한다. 테스트를 위해 사용자 원본을 바꾸지 않는다. 자동 캐시/원본 삭제 명령을 추가하지 않는다.

- 새 Vlog에는 촬영 날짜가 표시된 오프닝과 짧은 엔딩을 기본으로 생성한다. 날짜는 원본 촬영 메타데이터/사용자 지정에서 얻고 오늘 날짜나 파일 수정일로 지어내지 않는다. 구체적 문구와 스타일은 Skill을 따른다.
- Claude Code 작업 공간은 분리되어 있다: `analysis/lanes/claude/`, `preview/claude/`, `output/claude/`, `config.claude.json`, `scripts/vlog-claude.sh`, `.claude/`, `CLAUDE.md`. Codex는 이 경로를 읽기만 하고 수정·삭제하지 않는다. Claude는 Codex의 기본 작업 공간(`analysis/timeline.json`, `analysis/revisions/`, `preview/`·`output/` 바로 아래)을 수정하지 않는다. `src/`, `analysis/analysis.json`, `analysis/cache/`는 공유한다.
