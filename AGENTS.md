# AGENTS.md

이 문서는 이 저장소에서 에이전트가 반드시 따를 작업 규칙이다. 기술 철학과 권장 워크플로우는 `skills.md`를 참고하되, 충돌하면 이 문서가 우선한다.

## 1. 프로젝트 정체성

이 저장소는 채용 탐색, 기업 분석, 이력서/자기소개서 수정, 면접 전략 생성을 돕는 AI-agent 프로젝트다.

인접한 `../quantitative_trading` 프로젝트는 작업 지침 문서 구성과 에이전트 운용 방식의 참고 대상일 뿐이다. 이 프로젝트를 퀀트, 시계열, 트레이딩 연구 프로젝트로 취급하지 않는다.

## 2. 세션 시작 규칙

작업을 시작할 때 아래 파일을 우선 읽는다.

1. `AGENTS.md`
2. `skills.md`
3. `process.md`
4. `history.md`
5. `conversation_l2_cache.md`
6. 요청과 관련된 코드, README, `knowledge/`, `more_info/`

## 3. 사실성 가드레일

- 사용자의 경력, 기술, 성과, 수치, 자격, 프로젝트 경험을 지어내지 않는다.
- `knowledge/`와 `more_info/`에 있는 사실과 사용자가 대화에서 직접 제공한 사실을 우선한다.
- JD에 요구사항이 있더라도 근거 없는 경험으로 채우지 않는다.
- 자기소개서와 이력서 문장은 설득력보다 사실성을 먼저 만족해야 한다.
- 기업 분석은 출처가 불분명한 평판, 추정, 과장 표현을 그대로 단정하지 않는다.

## 4. 코드 작업 경계

아키텍처는 3개 에이전트 파이프라인이다(다이어그램: `images/project_archi.png`, 상세: `README.md`).

- **Agent 1 (Job Search & Resume Reviser)**: `job_agent/agents/job_hunter.py`(공고 탐색·기업분석, 실행 가능), `job_agent/agents/resume_reviser.py`(이력서/자소서 맞춤화)
- **Agent 2 (Master Resume Builder)**: `job_agent/documents/source.py`, `job_agent/documents/library.py`(명시 선택 DOCX 추출·문단 근거 연결·검수된 공통 이력서 JSON/Markdown 컴파일). 완전 자율 사실 정규화나 문장 사실성 자동 판정은 미구현이며, 원문 검수가 필요하다.
- UI 단일 입력 규격: `job_agent/documents/profile.py`의 `ResumeProfile` / `job-agent.resume/v1`(`docs/resume_input.md`). 수정 시 검수 승인 해제, 미검수 값 실행 차단. 저장본 `result/resume_profile/`은 개인정보로 Git 제외. 기존 CLI 원문/master 형식은 호환성 유지.
- 정형 반복 입력은 `documents/sections.py`의 단일 스키마와 필드의 선택적 `items`로 보관한다. `value`는 결정론적 표시 텍스트이며 불일치를 차단한다. Word·Markdown·JSON은 같은 프로필 입력이다. 공개 DOCX는 브라우저 fflate/DOMParser로만 읽고 내려받으며 서버 추출 API 차단은 유지한다. 임의 문서의 사실 분류/날짜 추정이나 포털의 반복 행 생성으로 설명하지 않는다. 정리 결과는 명시 검수 후 회사 변환에 선택하며 공통 원본을 덮어쓰지 않는다.
- **Agent 3 (ResumeOps Sync)**: `job_agent/agents/site_resume.py`, `job_agent/browser/mapper.py`, `job_agent/browser/connector.py`, `job_agent/browser/filler.py`(사이트별 규격 변환·DOM 수집·폼 매핑·검수된 필드 입력). UI의 `job_agent/browser/sync.py`는 명시 승인 후 저장·재접속 확인을 수행한다. Playwright 반자동이며 로그인·최종 검수·지원은 사용자, 기존 CLI 최종 저장은 수동이다.
- 공용 엔진: `job_agent/core/engine.py`(`LangGraphAgentEngine`)
- LangChain/LangGraph 예제 및 실험: `job_agent/examples/langchain_demo.py`, `job_agent/examples/langgraph_demo.py`
- 기타 실험: `job_agent/examples/construction.py`
- 사용자 사실 데이터: `knowledge/`, `more_info/`
- 별도 Vercel 공개 배포는 `hosting/build.py` allowlist export만 사용한다. 기존 로컬 환경/자료/세션을 삭제·이동하지 않는다. private backup ZIP은 `.env` 포함 가능하므로 업로드 금지. 공개 프로필/기록은 탭 RAM, 실행은 요청별 정리·개인 모델/검색/포털 차단·no dotenv/no 파일·DB·내용 로그. Supabase 미연결. 실제 HTTPS 검증/CLI 배포 성공과 GitHub 자동배포·MCP OAuth 연결 상태를 구분한다(`docs/public_hosting.md`).
- 플랫폼 연결은 `ui/local_kit.py`의 코드 전용 ZIP과 `--handoff-origin`으로 본인 PC의 로컬 UI에 이력서만 전달한다. 정확한 origin/opener/source 확인 및 웹 전달 동의·로컬 가져오기 승인 필수. 비밀번호/OTP/쿠키/storageState 입력·업로드와 운영자 포털 세션 공유 금지. 로컬 API·관리 토큰·로그인 세션을 공개 웹에 전달하지 않는다. 로그인/MFA/보안 확인은 본인 PC의 전용 브라우저에서 직접 수행, `ResumeSync.status`는 보수적 상태 안내이며 인증 성공 보장이 아니다. 회사 사이트/휴대폰만의 무설치 자동화를 구현했다고 설명하지 않는다.
- UI 자체 LLM 연결은 `job_agent/ui/models.py`의 OpenAI 호환 API이며 주소·키 변경은 로컬 소유자만 허용한다. 연결 키는 메모리에만 유지하고 이력서/JD 전송은 실행별 동의가 필요하다.
- Cloudflare 외부 공유는 로컬 소유자의 동의로 시작한다. `--public-demo`는 무코드 브라우저별 메모리 전용 작업 공간(`ui/visitors.py`, `WorkspaceService(ephemeral=True)`)을 제공한다. 방문자 이력서·결과를 앱 파일/DB/내용 로그에 기록하지 않고 사용자 다운로드만 허용한다. localStorage/IndexedDB 자동 저장 없음. 세션 시작 1시간 후 만료·60초 이내 메모리 참조 정리, 명시 삭제/정상 종료도 정리. OS 스왑/덤프·Cloudflare 처리까지 무저장을 보장하거나 법적 준수를 인증했다고 표현하지 않는다. 운영자 파일·키·포털 세션 재사용 금지 및 모델/검색/DOCX/실제 저장 차단 유지. 기존 개인 로컬 저장과 인증 공유는 별도 모드다.
- 외부 허용 모델은 서버 CLI `--remote-providers`로만 지정한다. 기본 외부 LLM 없음만 허용하며 OpenAI/Gemini에는 `--allow-remote-paid-api`, Tavily에는 `--allow-remote-web-search`가 별도로 필요하다. 공개 정책의 UI/API 변경과 원격 소유자 권한/코드는 제공하지 않는다. 개인 키를 외부 사용자 BYOK처럼 취급하지 않는다.
- 결과물: `result/`
- **원칙: 최종 검토와 지원서 제출은 사용자(Human-in-the-loop).** 2026-10-08 사용자 요청으로 UI의 명시적 항목·저장 동작 검수/동의 후 기존 이력서 필드의 입력·저장을 허용한다(`job_agent/browser/sync.py`). 저장 확인은 선택 필드의 재접속 readback 기준이며 전체 이력서 완성/지원 완료가 아니다. 공개 설정·동의·제출은 조작하지 않는다. 기존 CLI filler는 저장 수동 정책을 유지한다.

로컬 에이전트 스킬, 플러그인 캐시, 개인 설정은 `.agents/`, `.codex/`, `.claude/settings.local.json`에 둘 수 있지만 Git에 커밋하지 않는다.

## 5. 변경 원칙

- 먼저 검색하고 읽은 뒤 수정한다.
- 프롬프트, 도구, 상태 그래프, 파일 입출력 변경은 작게 나누어 수행한다.
- 기능 변경에는 가능한 최소 검증을 붙인다.
- 생성 결과나 개인정보성 파일을 커밋 후보에 올리지 않는다.
- 변경 후 필요한 내용은 `history.md`, `process.md`, `conversation_l2_cache.md` 중 맞는 곳에 갱신한다.

## 6. Codex/Claude 병행 작업 규칙

루트 `../AGENTS.md`와 `../tools/isolation/README.md`의 공통 프로젝트 격리 규칙도 따른다.
사용자 최신 정책은 추가 worktree 없이 단일 체크아웃이다. 모든 폴더가 현재 브랜치를 공유하므로 한 프로젝트씩 작업하고 미커밋 변경을 정리한 뒤 전환한다. 프로젝트 파일만 명시적으로 staging/commit하고 해당 브랜치를 명시해 push한다.
2026-10-08 루트 정책 설정 요청에 한해 공통 규칙/검사와 stock/apple AGENTS를 추가한다.
일반 기능 커밋은 계속 `resum/`만 포함하고 공통 정책 변경은 별도 커밋으로 분리한다.

이 저장소는 Codex와 로컬 Claude를 병행해서 사용할 수 있다. 어느 에이전트가 작업하더라도 흐름이 끊기지 않도록 아래 규칙을 따른다.

### 브랜치 규칙 (강제)

- **이 프로젝트 폴더(`resum/`)의 모든 작업은 `job_agent` 브랜치에서만 수행한다.** 새 기능/수정 브랜치를 별도로 파지 않는다. 작업 시작 시 `job_agent`가 아니면 먼저 체크아웃한다.
- **머지 흐름은 `job_agent` → `develop` → `main`** 순서다. 다른 방향(예: `main`에서 직접 작업, `job_agent`에서 `main`으로 직행)은 금지한다.
- 커밋은 `job_agent`에 선형으로 쌓고, 승격이 필요할 때만 `develop`으로, 검증 후 `main`으로 머지한다.
- 인접 폴더(`../stock`, `../quantitative_trading`)는 이 프로젝트 작업 범위 밖이며 `job_agent` 커밋에 포함하지 않는다.
- 사용자 재확인(2026-10-06): 작업 준비를 위해 `stock`, `main`, `develop`을 `job_agent`에 병합하지 않는다. 프로젝트 브랜치 전환과 다른 프로젝트 이력 통합을 혼동하지 않는다.

### 작업 시작

- `git status --short --branch`로 현재 브랜치와 미커밋 변경을 먼저 확인한다.
- `conversation_l2_cache.md`에서 최근 사용자 의도와 주의점을 읽는다.
- `history.md`에서 최근 변경 이력을 확인한다.
- 이미 다른 에이전트가 남긴 변경이 있으면 되돌리지 말고 그 위에서 이어서 작업한다.

### 작업 중

- Codex와 Claude 모두 이 파일(`AGENTS.md`)을 최상위 규칙으로 따른다.
- 로컬 도구별 세부 지침이 다르더라도 프로젝트 정책, 개인정보 보호, 사실성 가드레일은 이 문서를 우선한다.
- 큰 변경은 파일 단위로 작게 나누고, 중간 결정을 `process.md`에 반영한다.
- 장시간 작업이나 맥락이 중요한 작업은 `conversation_l2_cache.md`에 짧게 갱신한다.

### 작업 종료

- 무엇을 바꿨는지 `history.md`에 날짜별로 요약한다.
- 다음 에이전트가 이어받아야 할 의도, 제약, 남은 작업은 `conversation_l2_cache.md`에 갱신한다.
- 검증을 실행했다면 명령과 결과를 남기고, 실행하지 못했다면 이유를 남긴다.
- 커밋 전에는 `.agents/`, `.codex/`, `.claude/settings.local.json`, 개인정보 파일, 생성 결과물이 포함되지 않았는지 확인한다.

## 7. 문서 역할

- `AGENTS.md`: 강제 규칙, 실행 경계, 세션 시작 규칙
- `skills.md`: 기술 철학, 에이전트 설계 기준, 권장 워크플로우
- `process.md`: 현재 운용 절차와 반복 작업 방식
- `history.md`: 의미 있는 변경 이력
- `conversation_l2_cache.md`: 최근 사용자 의도와 제약의 압축 캐시
- `CLAUDE.md`: 로컬 Claude 계열 도구가 `AGENTS.md`를 따르도록 연결하는 진입 문서
