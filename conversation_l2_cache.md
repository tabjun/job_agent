# conversation_l2_cache.md

## 최근 사용자 의도

- 2026-10-07: 고정 플랫폼뿐 아니라 회사 자체 채용 URL에 맞춰 그때그때 변환하는 기능 요청. `SiteRegistry`/`ApplicationAdapter`, 등록·수집·근거 기반 변환·검수 입력 CLI 추가. 가상 회사 Chromium 통합 검증, 실회사 사이트는 미검증. 회사 문항 작성·파일/동의/custom UI·최종 저장/지원은 아직 사용자 검수/수동 영역.

- 2026-10-07: 인크루트 2단계 인증 완료. 외부 취업 폴더 자료를 참고해 실제 이력서 작성 및 전체 코드 커밋/push 요청. 재직 형태 정규직 직접 확인. 개인 원문은 push 대상이 아니다.

- 2026-10-06: ALIO는 쓸모없으므로 연동 제외. 우선 대상은 캐치·잡코리아·사람인·원티드·인크루트. 로그인된 실제 이력서 편집 화면의 DOM/F12 정보를 조사하여 Playwright 자동화로 연결한다.

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
- 과거 ALIO API TODO는 2026-10-06 사용자 요청으로 취소.
- 사용자 관심: 전체 슈퍼바이저(triage/라우터) + 하위 전문 에이전트 구조. 참고: `../ai_agent/part9_customer_support_agent/README.md`의 입력 가드레일→분류 에이전트→전문 에이전트→출력 가드레일 mermaid 패턴.
- `job_agent/agents/site_resume.py` 1차 틀 추가: 사이트별 프로필을 바탕으로 이력서 입력 패키지(JSON/Markdown)를 `result/site_resumes/`에 저장한다. 실제 사이트 로그인/저장 자동화는 아직 하지 않는다.
- `job_agent/browser/mapper.py` 추가: 사람인, 원티드, 잡플래닛, 캐치, 잡코리아, 링크드인의 공개/로그인 페이지를 정적 fetch 및 Playwright로 접근해 폼/버튼/selector 스냅샷을 저장한다.
- `job_agent/browser/connector.py` 추가: `job_agent/agents/site_resume.py`가 만든 입력 패키지와 Playwright 폼 스냅샷을 selector 매핑 계획으로 연결한다.
- Playwright 패키지는 `.venv`에 `uv pip install --python .\.venv\Scripts\python.exe playwright`로 설치했다. 번들 Chromium 대신 로컬 Chrome/Edge 실행 파일을 자동 탐색하도록 구현했다.

## 다음 TODO

- 최신 실제 작성 기록: `docs/resume_authoring.md`. 6개 DOCX 기반 공통 master와 근거는 ignored `result/master_resume/`, `result/resume_library/`. 5사이트 입력을 이번에는 원복하지 않음. 캐치/잡코리아/사람인/인크루트 최종 저장은 사용자, 원티드 자동저장 및 새로고침 유지 확인(필수 UI 100%). 인크루트 STEP02 자기소개는 로컬 초안만 준비. 실제 최신 DOCX+master 통합 포함 12 tests 통과.

- 2026-10-06 실제 DOCX 입력 테스트 진행: 원문 추출기 `job_agent/documents/source.py`, ignored 결과 `result/source_resume_test/`. 캐치/잡코리아/사람인 경력 572자, 원티드 소개 392자 실제 입력 후 원래 값 복원. 원티드 blur 자동저장 발견, 복원 새로고침 검증. `docs/real_source_test.md` 참조. 개인 원문 통합 포함 10 tests 통과.

- 5개 사이트 실제 편집 DOM 조사 완료: `docs/site_form_observations.md`. 인크루트 2단계 인증은 2026-10-07 완료.
- 해당 사이트의 실제 이력서 입력 화면 필드, 필수값, 글자수 제한을 확인한다.
- `uv run job-agent form-map --mode playwright --headed --interactive --sites <site>`로 전용 프로필을 열고 Enter마다 편집 화면/팝업/iframe을 수집한다. 값 미리보기 기본 제외.
- Playwright/브라우저 자동화는 사용자 로그인 세션과 최종 저장 확인 절차를 포함해 별도 단계로 구현한다.
- `job_agent/browser/filler.py` 구현됨: 개별 approved mapping만 검증/입력, blur 후 readback. 10-06 smoke test는 원복했고, 10-07 실제 작성 초안은 남겨뒀다. 원티드 custom 회사/날짜/재직형태/학력 선택은 브라우저 도구로 실제 수행했지만 재사용 Python adapter는 미구현. 원티드 자동저장 영속성은 확인됐으며 다른 사이트 저장 영속성과 Python CLI 실사이트 흐름은 추가 검증 필요.

## 현재 주의점

- OpenAI 기본 모델은 사용자 요청으로 `gpt-6-luna`로 변경. `OPENAI_MODEL` 재정의 가능. Responses API + medium 추론, store=False, 암호화 추론 상태 재전달. 답변 표시는 `.text` 사용. 이전 gpt-5-mini 실호출 기록을 Luna 검증으로 오인하지 말 것. Luna 실계정 접근/생성 품질은 아직 미검증이며 회귀 검증은 외부 호출 없는 모의 API 기준.

- 사용자는 `job_agent`에서 이력서 프로젝트만 작업하기를 재확인했다. `stock/main/develop`을 작업 준비 명목으로 병합하지 않는다. 잘못된 main 병합은 `b05617b`로 되돌림, 이번 사용자 push 요청에 정정 커밋도 포함한다. `resum/` 이전 작업 백업은 stash에 보존.

- `quantitative_trading/`은 별도 프로젝트로 취급한다.
- 이력서/자소서 관련 출력은 사실성 가드레일을 최우선으로 둔다.
- 개인 자료, 결과물, 키 파일은 커밋하지 않는다.
- 작업 전후로 `git status`, `history.md`, `conversation_l2_cache.md`를 확인/갱신한다.

## 2026-10-07 구조 정리

- 루트 Python 파일을 `job_agent/{core,agents,documents,browser,sites,examples}/`로 분리. 지침 Markdown은 기존 요구대로 루트 유지.
- 문서/세션/입력/저장 상태를 `DocxReader`, `ResumeLibrary`, `UserContextLoader`, `BrowserSession`, `FormFiller`, `ArtifactStore`, `ProjectPaths`로 캡슐화.
- 실행은 `uv run job-agent <명령>` 또는 `python -m job_agent <명령>`. 상대 자료/출력 경로는 프로젝트 루트 기준이며, 자료·결과·로그인 프로필 위치는 유지.
- 개인 DOCX와 검수 마스터 포함 19 tests 통과. 기존 master JSON/MD 및 5개 사이트 JSON 재컴파일 결과 동일. 계정 화면에는 이번 변경으로 입력하지 않음.
- 안티그래비티 프로젝트 설정 참조 제거. 빈 `.antigravitycli/` 폴더 삭제는 실행 정책으로 차단되어 물리 폴더만 남음. 전역 앱은 변경하지 않음.
