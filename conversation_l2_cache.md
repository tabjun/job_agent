## 전체 변경 커밋·푸시 요청 (2026-10-09)

- 최신 사용자 요청: 개인정보/생성물 제외한 모든 현 변경 커밋·push. 공통 정책과 resum 구현을 분리하고 origin/job_agent만 대상, 타 브랜치 merge 없음.
- 전체 테스트 113개(109 통과·4 opt-in 제외), isolation 9개 통과. lock/Ruff/staged diff 검사 통과. GitHub push가 Vercel 재배포 의미는 아님.
- 공통 훅은 이제 .git/project-isolation/.githooks에 설치되어 브랜치 전환으로 tracked 규칙이 제거되어도 유지됨. 정책 수정 후 python tools/isolation/install.py로 재설치. 다른 clone에는 자동 적용되지 않음.

## 워크트리 취소·단일 체크아웃 (2026-10-09, 최신 의도)

- 사용자가 관리 번거로움 때문에 worktree 제거를 명시 요청. 추가 toy-stock/toy-apple/toy-integration과 .code-workspace/외부 안내문 제거. 원래 root/resum와 모든 기존 개인 자료/변경 보존. 브랜치는 삭제하지 않음, 현재 job_agent/HEAD 8f015d1, stock ref dd316ef 유지.
- 공통 경로 소유권 훅 유지. 프로젝트별 명시 staging/검수/commit 및 origin 해당 branch 명시 push. 단일 root의 모든 폴더는 현재 브랜치를 공유하므로 병렬 브랜치 작업 불가능; 한 프로젝트씩 변경 정리 후 전환. 강제 checkout/자동 stash/타 프로젝트 병합 금지.
- 이번 요청에서 커밋·푸시·병합 없음. 아래 worktree 분리 이력은 과거 기록이며 더 이상 운영 경로 아님.

## 프로젝트별 작업 폴더 분리 (2026-10-09, 이후 취소)

- 사용자 승인으로 실제 linked worktree 생성 완료. 기존 toy_agent_project/resum(job_agent) 유지, Analysis/toy-stock/quantitative_trading(stock), toy-apple/apple(apple), toy-integration(develop). Analysis의 프로젝트별 .code-workspace를 열 것. 기존 root/quantitative_trading에서 브랜치 전환하지 말 것.
- 서버 stock 커밋·푸시 후 새 stock 폴더에서 git pull --ff-only origin stock. 최신 dd316ef(15커밋 fast-forward), apple/develop 최신. 서버는 변경하지 않음. job_agent에 다른 브랜치 병합·커밋·푸시 없음.
- 루트 tools/isolation 경로 보호 + 절대 core.hooksPath 공유. stock 소유 경로는 quantitative_trading과 legacy stock. 기존 stock 연구 훅과 LFS 유지. isolation 테스트 8개 통과, stock/apple 실제 훅 성공.
- 기존 모든 개인 자료/환경/미커밋 코드 보존; 무시된 데이터·키·.venv 자동 복사 아님. 별도 데이터 복사 질문은 응답 전 기본 보존 정책 적용. 새 worktree .githooks LFS 4개 미추적 파일은 그대로 보존, 커밋하지 말 것. 훅은 로컬 원래 루트 의존이며 다른 clone에 자동 배포되지 않음.

## 더블클릭 PC 연결 (2026-10-08)

- 최신 요청은 일반 사용자용 설치/실행 간소화. ZIP 루트 `Start-Resume-Connector.cmd`, START-HERE.txt·한국어 README, `ui/launcher.py` 추가. EXE가 아니라 Windows 실행 스크립트이며 uv 부재 시 공식 WinGet 설치 여부 질문, locked sync 후 loopback 서버·브라우저 열기. 정책 우회/자동 약관 수락 없음.
- 웹 다운로드에서 현재 정확한 origin을 connector.json으로 설정. 개인 자료·세션·키를 배포하지 않음. 기존 프로젝트에 덮지 않고 새 폴더에 압축 풀기; 창 유지·Ctrl+C 종료·PowerShell/Linux/macOS 수동 안내 제공.
- 배포 완료: `result/hosting/doubleclick-connector-release-20261008`, `dpl_DsUwjApxmerqLQJZoqeUTM8tQW9k`, 고정 링크 동일. 관련 테스트 22개 통과, 공개 UI 다운로드 실제 ZIP에 실행 파일·origin 확인. Windows cmd 테스트는 uv stub으로 sync/start/실패 차단 검증; 추출 ZIP Python 런처는 실제 loopback 서버 시작 확인. 새로운 PC의 uv/WinGet 최초 설치 자체는 미검증. Git 병합/커밋/푸시 없음.

## 실제 화면 사용 예시 (2026-10-08)

- 사용자 요구: Codex 안에서 직접 수행하면서 서비스 탭별로 캡처를 넣을 것. `static/tutorials/` 가상 자료 14장, 서비스별 gallery·확대 dialog·플랫폼 연결 예시 추가.
- 공고/정리 실제 실행, Word 빈 양식 다운로드, 공개 HTTPS→임시 본인 PC 승인 전달, 별도 테스트 양식 소개 실제 입력·저장·재접속 확인 성공. 실제 5개 포털 계정 저장 검증은 아니며 사진 설명에 구분.
- `ui/tutorials.py` allowlist만 서버/hosting/연결 ZIP에 포함. 개발용 `tests/capture_tutorial_fixture.py`는 테스트 전용·배포 제외. 운영자 개인정보·키·세션 사용 없음.
- 최신 배포는 `result/hosting/tutorial-screens-release-20261008`, `dpl_29ZJAEz4cWvRHACqfvJNAC1qWuGH`; 고정 링크 `https://job-agent-resume-web.vercel.app/#examples/profile`. 예시 캡처 배포/확대 실제 확인. 전체 105개(101 통과·4 제외), 자산 추가 3개, 공개 HTTPS 2개 통과. 가상 테스트 서버 종료. Git 병합/커밋/푸시 없음.

## 플랫폼 전환 요청 (2026-10-08)

- 5개 채용 플랫폼 전환·저장이 메인. `#prepare`에 다중 체크/진행, 회사 자체 JSON은 고급 접힘.
- 웹에서 이력서/선택 목록만 본인 PC popup에 승인 전달. 세션은 사용자 PC 전용 persistent profile 재사용. 기존 개인 Chrome 쿠키 추출/웹 인증 자료 업로드 금지.
- 로컬 재검수 후 선택 사이트 진행 → 로그인/MFA → 사이트별 검수·저장. 정확한 단일 연결/성공 연결 선제안, 저장 승인은 유지.
- 반복 경력 행 생성·지원서 제출 자동화 아님. 테스트 DOM 실제 저장/readback과 실제 포털 5곳 검증을 구분할 것.
- 고정 주소 `https://job-agent-resume-web.vercel.app/#prepare`, 최신 코드 전용 export `result/hosting/portal-workflow-release-20261008`, deployment `dpl_HJNQTacTkq9vVTj9WaWw9fLZccKD`. 오래된 연결 도구 ZIP은 새 UI 코드가 없으므로 필요 시 새 ZIP을 별도 폴더에 설치하고 원래 로그인 프로필/자료는 삭제·이동하지 말 것. 원래 서버 재시작/포털 계정 실제 저장은 수행하지 않음.

## 최신 UI 요청 (2026-10-08)

- 사용자는 첫 탭에 목적/흐름 설명을 원함. `#guide` 기본 화면에서 공고 탐색 독립, 작성→정리→검수→변환 연계 안내.
- 결과 기록·외부 공유 링크 UI 제거. 고정 Vercel 주소 유지. 공개 transport 이전 결과 목록 제거; 현재 결과 다운로드 필요. 기존 로컬 자료/CLI 기록·공유 기능은 삭제하지 않음.
- 회사 양식 파일 준비/본인 PC 연결/MFA/수동 회사 사이트 저장 한계를 솔직히 설명. 구형 이미지의 자율 AI/YAML 기능을 완성으로 홍보하지 않음.

# conversation_l2_cache.md

## 최근 사용자 의도

- 정형 입력 공개 배포 완료: 동일 고정 주소 `https://job-agent-resume-web.vercel.app`, export `result/hosting/structured-resume-20261008`, 실제 HTTPS 정형 browser workflow 1 test(별도 개인 원문 test는 공개 검증에서 skip) + hosting 5 tests 통과. 전체 102 tests/3 skip 성공과 개인 DOCX의 localhost 검증 완료. 기존 입력 탭은 새로고침 시 사라지므로 다운로드 후 업데이트 권장. 코드/빈 양식만 배포, 개인 자료/키/세션 보존·미업로드. 현재 브랜치는 job_agent, commit/push/merge 없음.

- 최신: JSON/한 칸 입력 대신 일반인용 Word 양식·항목별 반복 입력 요구. sections.py 단일 정형 스키마와 v1 필드 선택 items, 기술/경력/자격/수상/프로젝트/학력/어학/교육/활동/논문/특허/링크 추가·삭제, 재직 중/날짜 검증 구현. Word 기본·MD·JSON 다운로드/업로드를 브라우저에서 처리(공개 서버 DOCX 추출 API는 계속 금지). 일반 DOCX는 원문 보존·직접 분류, 가져오기 검수 해제. 정리 결과 명시 검수→회사 변환에 선택하되 원본 유지. 취업 폴더의 공통 DOCX/텍스트 PDF 구조 참고, 개인 내용 공개 코드/양식에 금지. 전체 102 tests 실패 없음/3 skip(실제 private DOCX 포함). Word COM→bundled PDFium으로 6+3페이지 모두 시각 확인. 같은 고정 Vercel 주소로 별도 code-only export 배포 중, job_agent/원본 로컬 환경 보존·Git commit/push 미실행.

- 최신 요청: root monorepo의 stock/apple/resum 프로젝트끼리 간섭하지 않고 develop에서 통합. root `AGENTS.md`, 각 프로젝트 AGENTS, `tools/isolation/projects.json`/checker/runbook/tests, `.githooks/pre-commit` 추가. 현재 job_agent 유지, staged 소유권 검사 활성화(`core.hooksPath=.githooks`, 기존 비어 있는 퀀트 훅 경로 대체). 6개 임시 Git 테스트로 cross-project/rename/range 차단과 독립 병합 검증. 실제 프로젝트 브랜치 merge/commit/push 없음. 규칙-only 커밋의 다른 브랜치 배포는 아직 미수행; 기존 대규모 resume 변경과 분리해야 함. 동시 작업은 별도 worktree, root 공통 수정은 별도 명시 요청/governance-only commit. 충돌 완전 방지는 보장하지 않음.

- 재개 시 우선: 공개 배포 완료, 고정 주소 `https://job-agent-resume-web.vercel.app`(Cloudflare 아님, 노트북 종료해도 웹 사용). 실제 HTTPS 호스팅 5 tests 성공, 전체 96 tests/3 skip 성공. 기존 `.env` 백업 동일/venv/개인 프로필 존재 확인, 기존 Cloudflare 서버 보존. 최종 API 파일 top-level handler class 필요(Vercel 정적 인식), `functions`+public 설정으로 성공. GitHub 자동배포 미연결, CI 템플릿 미활성, MCP OAuth 미완료/CLI 인증 완료를 구분. 커밋/push는 이번 배포 요청으로 수행하지 않았고 모든 변경은 `job_agent` 작업 트리에 남아 있다.
- 재개 검증: 실제 HTTPS 호스팅 5 tests 재통과, Vercel→본인 PC 이력서 전달·이중 승인·검수 해제·파일 저장 분리 연결 1 test 성공. Vercel 사용자 환경변수 없음. 최종 배포 입력은 ignored `result/hosting/job-agent-resume-web-final`, private snapshot은 `result/hosting/backups/`(업로드 금지). 공개 고정 주소는 같고 채용사이트 자동 저장에는 여전히 사용자 본인 PC 연결 도구가 필요하다.

- 최신: 노트북 서버에서 Vercel로 공개 배포하되 기존 환경 삭제 금지·환경 복사·무료 자원 요청. `hosting/build.py` private `.env` 포함 가능 로컬 ZIP과 코드 allowlist export 분리, 기존 `.venv`/자료/결과/세션 유지. 공개 탭 RAM 프로필/기록과 기존 Python 요청 단위 함수 구성, 개인 API/검색/포털 차단·no dotenv/no body log/finally close. Supabase 미연결, GitHub CI 템플릿 미활성. 모바일 Vercel CLI 승인 완료, 공식 get-started.md 요청에 따라 CLI 전역 설치·Codex Vercel 플러그인 설치·global MCP 등록; MCP OAuth는 로컬 콜백 인증 미완료이며 배포 CLI 인증과 구분. Hobby 계정 확인 후 별도 export 배포 진행, 원본 monorepo 직접 GitHub 연결은 미성공. 기존 Cloudflare 서버는 보존. `docs/public_hosting.md` 참조.

- 최신: 실제 이용자가 플랫폼 로그인/2차 인증/편집 진입까지 따라 할 연결 흐름 요청. 플랫폼 연결 4단계 안내·코드 전용 ZIP·CLI exact `--handoff-origin`·opener/source/origin 검증 메시지·웹 전송 동의+로컬 가져오기 승인 구현. 이력서만 본인 PC로 전달, 세션/비밀번호/OTP/API 토큰 웹 전송 없음. 본인 PC 전용 브라우저 로그인/MFA 후 상태 확인/필드 검수/저장, 인증 화면 수집/입력 차단. 공개 서버의 포털 차단 유지, 사용자 PC에서는 로컬 파일/프로필 보관을 명시. 휴대폰만 무설치/회사 자체 사이트 자동 로그인은 미구현, JSON 다운로드·수동 반영 대안. 실제 HTTPS→격리된 로컬 UI 전달/승인 검증, 실계정 MFA 자동 완료로 설명하지 않는다.

- 최신 최우선: 노트북 서버에 방문자 파일을 남기지 않고 로컬 다운로드 또는 휘발성 사용, 웹 최하단 개인정보 안내 요청. 공개 `WorkspaceService(ephemeral=True)`는 파일/DB/내용 로그 없이 세션 RAM만 사용; 브라우저 자동 localStorage/IndexedDB 저장 없음. 1시간 세션/60초 주기 만료 정리, 임시 데이터 삭제 버튼, 최근 20개/약 10MB 기록 상한. 다운로드는 사용자 기기에만. 기존 개인 저장본은 유지. 하단 목적·항목·보유/파기·쿠키·Cloudflare·OS 스왑/덤프 한계 고지, 문의처 환경변수(공개 연락처 사용자 질문 중). 실제 기기 내 처리나 법적 준수 인증으로 설명하지 않는다.

- 최우선: 접근 코드를 UI에서 아예 제거 요청. `--public-demo`로 로그인 없이 브라우저별 빈 임시 공간 제공. 코드 표시/복사 UI 제거, 운영자 데이터·키·로그인 포털 세션은 공개하지 않음. 표준 JSON/직접 작성·공고 정리·이력서 정리·변환·결과 다운로드 지원, 공개 DOCX/실제 사이트 저장과 운영자 API 차단. 8시간 임시 세션/종료 정리이며 기존 개인 이력서가 휴대폰에 자동 나타나는 기능이 아님. 새 터널 사용, 주소/세션 값은 추적 파일에 남기지 않는다.

- 최신: 서비스별 사용법/예시 페이지 요청. 사용 예시 메뉴·맥락별 도움말·7개 주제와 안전한 가상 공고/JD 입력·빈 표준 양식 다운로드 구현. 예시의 자동 실행/프로필 덮어쓰기/사이트 저장 없음. fragment 직접 링크/로그인 후 복원 지원, 모바일/데스크톱 실제 공유 확인. 서버 자원/모델 숨김 유지, 현재 공유 주소는 그대로이며 추적 문서에 남기지 않는다.

- 최신: 외부에는 `LLM 없음`을 포함한 처리 모드/모델 선택 자체를 노출하지 않음. 초기 HTML 숨김·로컬 소유자만 표시, 원격 화면 전환에도 유지. 모델명/토큰 지표·기록 공급자 이름·연결 메뉴 숨김. 서버 CLI 자원 권한은 그대로, 기존 공유 URL 유지. 일반 방문자는 작업 입력/결과 중심으로 사용.

- 최우선 재확인: 외부 방문자에게 운영자 OpenAI/Gemini 존재/선택 및 과금 동의를 보이지 않게 함. `RemotePage`로 초기 HTML부터 비허용 모델/검색 선택지 제거, 외부 과금 문구는 전송 동의로 변경. 방문자 동의로 권한을 바꿀 수 없고 서버 CLI 명시 변경만 허용. 기존 유료 호출 차단 유지.

- 최신 정정이 우선: 외부 공유의 모델 ON/OFF 및 소유자 코드 삭제. 서버 CLI `--remote-providers`로만 정책 지정, 기본 외부 LLM 없음. 자체 서버도 명시 허용 필요. 유료 개인 모델은 `--allow-remote-paid-api`, Tavily는 `--allow-remote-web-search` 별도 운영자 플래그. 공개 사용자가 운영자 키/자원을 켜지 못하게 HTTP 정책 변경도 제거. 이전 소유자 터널/코드는 폐기. BYOK 사용자별 격리는 미구현.

- 최신: 사용자가 화면에서 외부 모델 ON/OFF 설정 요청. 공유 탭에 자체/OpenAI/Gemini 공개 설정과 과금 동의/저장 구현, LLM 없음 항상 허용. 원격 소유자용 별도 코드 추가로 휴대폰에서도 정책만 관리 가능. 방문자는 설정 불가, 키/주소/터널은 원격 소유자에게도 차단. 기본 개인 유료 모델 OFF, 15초 내 선택지 갱신·OFF 즉시 서버 차단·진행 호출 취소 없음. 코드/주소는 추적 파일에 남기지 않음.

- 외부 테스트는 LLM 없음/자체 LLM만 허용. OpenAI/Gemini UI 선택과 원격 config 정보 제거, 서버 요청 차단 구현. 개인 키의 외부 사용 금지, 로컬 사용은 유지. 자체 서버 연결은 로컬 소유자만 설정. 이전 공유 터널 중지·수정 서버 재생성으로 주소/코드 변경.

- 공유 링크 휴대폰 클릭의 Same origin required 오류 수정: cross-site 최상위 GET `/` 탐색은 로그인 shell만 반환, API/POST는 기존 same-origin 차단 유지. 기존 서버 대신 수정 서버의 새 Quick Tunnel 주소를 안내한다. 공유 관련 10 tests 통과, 링크·코드는 기록하지 않는다.

- 2026-10-08 최신: 사용자 보유 로컬/내부 LLM의 URL(IP·포트)·모델 ID·선택 API 키 연결 및 Cloudflare 외부 공유/클립보드 복사 요청. UI 모델 연결/자체 LLM 선택과 인증된 공유 탭 구현. 설정/키는 메모리 전용, 로컬 소유자만 관리. 외부 방문자는 접근 코드로 로그인해 같은 작업 공간 열람·편집·실행(비용 포함), 공유 중지/서버 종료 시 세션 폐기. 임시 Quick Tunnel이므로 PC 실행 필요·주소 재생성 변경; Named Tunnel 자동 구성/다중 사용자 격리/직접 모델 파일 로드는 미지원. 실제 모델 품질 테스트와 호환 HTTP fixture 검증을 혼동하지 말 것. 주소와 접근 코드는 추적 문서에 남기지 않는다.

- 2026-10-08 최신: 사용자는 외부에서 휴대폰으로 접속하여 localhost UI 조작 불가, PC에서 실제 저장까지 요청. 연결 Chrome으로 원티드 연구/AI 활용 자동저장·reload, 인크루트 경력/학력 섹션 저장 성공 알림·reload readback 검증 완료. 캐치는 기존 초안 readback만 확인(완성 저장 성공 미확인, 학력 주간/야간·학점/만점 질문 중). 잡코리아·사람인은 로그인 세션 만료 상태. 개인정보 증빙/백업 `result/site_sync/live-2026-10-08/`, 최신 범위 `docs/resume_authoring.md`. UI 전용 `ResumeSync` 프로필 E2E와 혼동하지 말 것. 공개 설정/동의/제출 금지 유지, 외부 접속을 위해 개인정보 UI를 무인증으로 공개하지 않는다.

- 2026-10-08 추가 요청: 빈 표준 JSON 다운로드·작성본 업로드/다운로드를 명확히 하고 UI 작성본으로 사이트별 저장까지 연결. `ResumeSync`/전용 loop worker와 UI 수집·매핑·동의·입력·저장·재접속 확인 구현. 사용자 요청에 따라 UI 명시 검수 후 저장 허용, 지원서 제출/공개 설정/동의는 계속 금지. 저장 전용 버튼 whitelist와 원티드 자동저장만, 불확실하면 완료/재시도하지 않음. 실제 5개 포털 저장은 아직 미검증이며 로컬 저장 fixture/모의 UI와 구분한다.

- 2026-10-08 추가: 사용자 입력 통로/형식을 하나로 통일해 LLM 없는 처리를 안정화 요청. `ResumeProfile`/`job-agent.resume/v1`, UI 공통 입력·저장·출처·검수·다운로드 연결. 이전 선택 DOCX 6개를 원문/해시 재검증하여 기존 검수 master 8개 필드 그대로 로컬 표준 저장본으로 이전. 새 자료 전수 스캔/임의 사실 파싱은 하지 않음. 수정 후 승인은 해제, 미검수 내용 실행 차단. 회사 반복 항목/custom UI는 별도 목적지 구현 필요.

- 2026-10-08: 공공기관/ALIO는 집에서 검토할 때까지 보류, 기존 민간 프로젝트로 복귀. 기본 자동화는 LLM 없이, AI 분석/문장 최적화는 선택·과금 동의 후 사용. 모델 선택·결과 비교·간편 실행 UI 요청. `job_agent/ui/` 추가, `ui` CLI와 Linux/PowerShell README 작성. 현재 공고 baseline은 직접 JSON 또는 별도 Tavily 검색 결과의 필터/정렬이며 무료 사이트별 스크래퍼/원문 마감 확인은 후속 작업. UI 회사 양식은 기존 검수 JSON 변환만, 실제 입력·저장 미실행.

- 2026-10-08: Agent 1이 단순 적합도보다 풍부한 정보를 주도록 JobPT/jobai-ai/career-ops/ai-job-search 및 추가 사례 조사 요청. `docs/agent1_landscape_2026-10-08.md`에 정적 구현 비교·라이선스·서비스 참고·도입 계획 기록, README 연결. 다음 구현은 날짜/공고 원문·상태/필수·우대/출처 계약 P0부터. 근거 기반 국내 기업·팀/조건/경력 방향 의사결정이 목표이며 아직 미구현. 다른 저장소 통째 도입이나 stock 병합 금지 유지.

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
