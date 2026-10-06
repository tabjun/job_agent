# history.md

## 2026-10-07

- 사용자 지정 외부 취업 폴더의 최신 공통 이력서/경력기술서 등 6개 DOCX를 근거로 공통 이력서 8개 블록 및 사이트별 공통 패키지를 작성. 개인 corpus/검수 초안/산출물은 ignored `result/`에만 보관.
- `resume_library.py` 추가: 명시 선택 DOCX 추출, SHA256 중복 제거, 원본 변경 및 추출문 변조 차단, 문단 참조 검증, 검수된 초안 컴파일. 의미상 사실성 판단은 수동 검수 범위다.
- 인크루트 사용자 2단계 인증 완료 확인 후 기존 이력서 편집 조사·작성. 5개 사이트 실제 경력/소개 작성, 잡코리아 자기소개 및 캐치 상세 기술서 추가. 원티드 회사/날짜/졸업/전공 선택과 사용자 확인한 정규직 반영, 자동저장 새로고침 검증. `docs/resume_authoring.md`에 작성 및 미작성 범위 기록.
- 실제 최신 원본 및 검수 master package의 로컬 Chromium 통합 포함 12개 테스트 통과. 사용자 요청으로 이 프로젝트 코드/문서/테스트 전부 커밋 및 `origin/job_agent` 일반 push 진행. 개인자료/다른 프로젝트는 제외, 다른 브랜치 병합 및 force push 금지 유지.

## 2026-10-06

- 사용자 지정 실제 DOCX로 `resume_source.py` 추가: 92개 원문 문단, 경력 572자/소개 392자, 문단 근거 및 SHA256 포함 사이트 패키지 생성. 개인 산출물은 ignored `result/source_resume_test/`에만 보관.
- 로그인된 실제 화면에서 캐치/잡코리아/사람인 경력 및 원티드 소개 실입력·포커스 이동 후 readback 검증. 모두 테스트 전 값으로 복원. 원티드 자동저장 확인 및 복원 후 새로고침 검증. 최종 저장/지원 클릭 없음. 인크루트 2단계 인증 대기.
- 입력기에 blur 후 검증 추가. 실제 DOCX → 패키지 → Python 입력기 로컬 Chromium 통합 포함 10개 테스트 통과. 실제 사이트 입력은 브라우저 도구를 사용했으며 Python CLI 사이트별 실행/전체 이력서 동기화는 미검증. `docs/real_source_test.md` 기록.

- 작업 준비 중 만든 `origin/main` → `job_agent` 병합(`2d8a29b`)이 다른 프로젝트 이력을 포함한 문제를 사용자 지적에 따라 정정. 되돌림 커밋 `b05617b`로 병합 전 트리 복원, `resum/` 자동화 미커밋 변경은 stash 백업 후 그대로 복원. 정정 커밋은 로컬이며 원격 push는 수행하지 않음.

- 사용자 요청에 따라 ALIO 연동 TODO 취소. 캐치·잡코리아·사람인·원티드 및 추가 요청한 인크루트 실제 화면 기반 자동화를 우선한다.
- 폼 수집기에 전용 persistent 프로필, Enter 반복 수집, 팝업 탭/중첩 iframe/open shadow DOM, 유일 selector 및 제한값·선택지 기록 추가. 입력값은 기본 제외, password/hidden은 항상 제외.
- 필드 연결에서 비편집·로그인용 필드 제외, contenteditable 지원, iframe/shadow 위치 보존, 동점/중복 목적지/글자수 초과 검토 표시 추가.
- 사용자 로그인 후 캐치/잡코리아/사람인/원티드 기존 이력서 편집 DOM 조사 완료. `docs/site_form_observations.md`에 개인정보 없이 selector/제한/팝업/readonly 관찰 기록. 인크루트 로그인 후 이력서 관리에서 2단계 인증 대기.
- `site_form_filler.py` 추가: 개별 검수 표시가 있는 필드만 실행, 기본은 검증만. 실입력은 `--apply`와 `APPLY` 필요. 실제 계정 값 변경/저장/제출은 수행하지 않음.
- 검증: `python -m unittest discover -s tests -v` 6개 통과. 실제 로컬 Chromium DOM으로 중복 id, multiline placeholder, iframe/shadow, 값 제외, 입력 확인, 중복 대상 및 길이 초과 차단 검증.

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
