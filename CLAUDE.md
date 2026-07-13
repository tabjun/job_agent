# CLAUDE.md

이 프로젝트에서 로컬 Claude 계열 도구는 `AGENTS.md`를 우선 지침으로 따른다. Codex와 Claude를 병행해서 사용하므로, Claude에서 작업하더라도 Codex가 바로 이어받을 수 있게 작업 상태를 문서에 남긴다.

작업 시작 시 함께 확인할 파일:

1. `AGENTS.md`
2. `skills.md`
3. `process.md`
4. `history.md`
5. `conversation_l2_cache.md`

로컬 스킬과 플러그인 캐시는 `.agents/`, `.codex/`, `.claude/settings.local.json`에 둘 수 있지만 Git에 커밋하지 않는다.

## Codex와의 인계 규칙

- 작업 시작 전 `git status --short --branch`를 확인한다.
- Codex가 남긴 미커밋 변경은 사용자 작업으로 보고 임의로 되돌리지 않는다.
- 의미 있는 변경 후에는 `history.md`에 변경 요약을 추가한다.
- 다음 작업자가 알아야 할 사용자 의도, 남은 TODO, 주의점은 `conversation_l2_cache.md`에 압축해서 남긴다.
- 반복될 절차나 정책은 `process.md`에 반영한다.
- 검증 명령을 실행했다면 명령과 결과를 요약하고, 실행하지 못했다면 이유를 남긴다.
