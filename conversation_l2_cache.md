# conversation_l2_cache.md

## 최근 사용자 의도

- 이 저장소는 quant 프로젝트가 아니라 AI-agent/resume 프로젝트다.
- `../quantitative_trading`은 작업 지침 구성 방식만 참고한다.
- `.agents/`, `.codex/`, caveman/plugin/Hugging Face 같은 로컬 스킬 묶음은 GitHub에 올리지 않는다.
- 원하는 구조는 폴더형 `conversation/`, `history/`, `process/`가 아니라 루트의 `conversation_l2_cache.md`, `history.md`, `process.md`다.
- `AGENTS.md`, `skills.md`, `README.md`를 중심으로 서버와 로컬 Claude/Codex가 같은 지침을 보게 한다.
- Codex를 쓰다가 Claude에서 작업하거나, Claude 작업 후 Codex가 이어받아도 흐름이 끊기지 않게 문서 기반 인계 규칙을 둔다.
- 새 목표: 이력서를 각 채용 사이트 양식에 맞게 편집하고, 나중에는 사이트에 저장까지 돕는 에이전트를 만들고 싶다.

## 진행 상황 (2026-07-01)

- agent1(Job Hunter) 실행 복구 완료. GPT 경로(`gpt-5-mini`)로 검증됨. Gemini는 `gemini-2.0-flash`로 코드 교체했으나 Google AI 키가 현재 free-tier 429(quota 0) — 계정 결제/한도 풀리면 동작.
- 사용자 의도: 지금은 "agent1만 전체 구성 가능"이 목표. agent2/3(Resume Reviser)이 장기적으로 더 중요하다고 했으나 그건 다음 단계.
- 다음 TODO: ALIO 공공기관 채용 API를 `job_hunter.py`에 실제 도구로 추가. 단, **사용자가 data.go.kr 명세를 직접 조사한 뒤** 진행. 명세 추측 금지(사실성 가드레일). 승인된 채용 API는 ALIO 하나뿐.
- 사용자 관심: 전체 슈퍼바이저(triage/라우터) + 하위 전문 에이전트 구조. 참고: `../ai_agent/part9_customer_support_agent/README.md`의 입력 가드레일→분류 에이전트→전문 에이전트→출력 가드레일 mermaid 패턴.
- `site_resume_agent.py` 1차 틀 추가: 사이트별 프로필을 바탕으로 이력서 입력 패키지(JSON/Markdown)를 `result/site_resumes/`에 저장한다. 실제 사이트 로그인/저장 자동화는 아직 하지 않는다.
- `site_form_mapper.py` 추가: 사람인, 원티드, 잡플래닛, 캐치, 잡코리아, 링크드인의 공개/로그인 페이지를 정적 fetch 및 Playwright로 접근해 폼/버튼/selector 스냅샷을 저장한다.
- `site_form_connector.py` 추가: `site_resume_agent.py`가 만든 입력 패키지와 Playwright 폼 스냅샷을 selector 매핑 계획으로 연결한다.
- Playwright 패키지는 `.venv`에 `uv pip install --python .\.venv\Scripts\python.exe playwright`로 설치했다. 번들 Chromium 대신 로컬 Chrome/Edge 실행 파일을 자동 탐색하도록 구현했다.

## 다음 TODO

- 우선 자동 저장 대상으로 삼을 채용 사이트 1개를 정한다.
- 해당 사이트의 실제 이력서 입력 화면 필드, 필수값, 글자수 제한을 확인한다.
- `site_form_mapper.py --mode playwright --headed --sites <site>`로 브라우저를 열고 사용자가 직접 로그인한 뒤 이력서 작성/수정 화면에서 selector를 재추출한다.
- Playwright/브라우저 자동화는 사용자 로그인 세션과 최종 저장 확인 절차를 포함해 별도 단계로 구현한다.

## 현재 주의점

- `quantitative_trading/`은 별도 프로젝트로 취급한다.
- 이력서/자소서 관련 출력은 사실성 가드레일을 최우선으로 둔다.
- 개인 자료, 결과물, 키 파일은 커밋하지 않는다.
- 작업 전후로 `git status`, `history.md`, `conversation_l2_cache.md`를 확인/갱신한다.
