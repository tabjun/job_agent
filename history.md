# history.md

## 2026-07-13

- 브랜치 작업 규칙 명문화: `resum/` 작업은 **`job_agent` 브랜치에서만** 수행하고, 머지 흐름은 **`job_agent` → `develop` → `main`**. `AGENTS.md §6`(강제), `process.md`(승격 명령 예시), `CLAUDE.md`(세션 시작 포인터)에 반영. 별도 feature/fix 브랜치 금지.
- 브랜치 정리: 앞서 나눴던 `fix/agent1-runnable`·`docs/handoff-and-architecture`·`feat/agent3-site-sync` 3개 브랜치를 `job_agent`로 선형 통합(ff-merge + cherry-pick) 후 삭제. 로컬 브랜치는 `main`·`develop`·`job_agent`·`stock`만 유지. `origin/job_agent`에 푸시 완료.

## 2026-07-01

- `.gitignore` 보강: `.agents/`, `.codex/`, `.antigravitycli/`, `.claude/settings.local.json`, `result/`, `self_introduction/`, `quantitative_trading/`를 명시적으로 무시. `knowledge/`는 `resume_example.txt`만 예외 추적, `more_info/`는 전체 무시.
- `more_info/guideline.txt`를 Git 추적에서 해제(`git rm --cached`). 로컬 파일은 보존. (개인 커리어 철학 파일이라 사용자 결정에 따라 해제)
- README의 과장 표현 수정: "7개 사이트 통합 검색/DART·잡플래닛 결합"은 사실과 다름. 승인된 채용 API는 공공기관 ALIO 하나뿐이고 민간 사이트는 Tavily 웹검색 best-effort임을 명시.
- **agent1(Job Hunter) 실행 복구 완료:**
  - `agent.py`: 종료된 `gemini-1.5-pro`(2025-09-24 단종)를 `gemini-2.0-flash`로 교체. `GEMINI_MODEL` env로 재정의 가능.
  - `temp_search.py`: 깨진 import `langchain_tavily.TavilySearchResults` → `TavilySearch`로 수정, 반환 dict의 `results` 키 처리 추가.
  - 검증: GPT 경로(`gpt-5-mini`)로 `llm_think→execute_tools→llm_think` 전체 루프 정상. `search_jobs` Tavily 검색 정상(52건 반환). Gemini 경로는 코드상 정상이나 현재 Google AI 키가 free-tier 429(quota=0) 상태 — 계정/결제 이슈.
- 미반영(다음 단계): ALIO API 도구화. 사용자가 data.go.kr 명세를 직접 조사 후 진행 예정. `job_hunter.py`는 아직 ALIO 미사용(Tavily만).
- **아키텍처 문서 정합화 (project_archi.png 기준):** 프로젝트를 3-에이전트 파이프라인으로 재정의. Agent1(Job Search & Resume Reviser, 실행가능) → Agent2(Master Resume Builder, 설계단계) → Agent3(ResumeOps Sync, 부분구현) + Human-in-the-loop.
  - `README.md`: 아키텍처 이미지(`images/project_archi.png`) 임베드, 3-에이전트 구조로 재작성, 각 에이전트 구현 상태를 과장 없이 표기, 사용법의 Gemini 1.5→2.0 반영.
  - `AGENTS.md §4`: 코드 위치를 3-에이전트 매핑으로 갱신, Human-in-the-loop 원칙 명시.
  - `.gitignore`: 상위 `*.png` 무시 규칙에서 `images/*.png`만 예외 처리(README 다이어그램 커밋용).

## 2026-06-30

- `quantitative_trading/`을 상위 Git 저장소에서 무시하도록 `.gitignore`에 추가했다.
- `.agents/`, `.codex/`, `.claude/settings.local.json`을 로컬 에이전트 설정으로 보고 Git에서 제외했다.
- 프로젝트 작업 지침을 폴더가 아닌 루트 Markdown 파일 체계로 정리했다.
- 추가 문서: `AGENTS.md`, `CLAUDE.md`, `skills.md`, `process.md`, `conversation_l2_cache.md`.
- Codex와 로컬 Claude를 병행 사용할 때 흐름이 끊기지 않도록 작업 시작/종료 인계 규칙을 `AGENTS.md`, `CLAUDE.md`, `process.md`, `conversation_l2_cache.md`에 명시했다.

## 2026-07-01

- `site_resume_agent.py`를 추가했다.
- 사이트별 이력서 저장 자동화의 1단계로, 원티드/사람인/잡코리아/점핏/캐치/LinkedIn 양식 프로필을 기준으로 JSON/Markdown 입력 패키지를 생성하도록 구성했다.
- 실제 사이트 로그인, 폼 자동 입력, 저장 버튼 클릭은 아직 구현하지 않고 후속 브라우저 자동화 단계로 분리했다.
- `site_form_mapper.py`를 추가했다. 정적 fetch와 Playwright로 사람인, 원티드, 잡플래닛, 캐치, 잡코리아, 링크드인의 페이지 폼 요소를 JSON 스냅샷으로 저장한다.
- `site_form_connector.py`를 추가했다. 이력서 입력 패키지와 DOM selector 후보를 연결하는 매핑 계획을 만든다.
- `.venv`에 Playwright 패키지를 설치했고, 로컬 Chrome/Edge 실행 파일을 사용하도록 구성했다.
