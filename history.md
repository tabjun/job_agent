## 2026-10-15: 독립 저장소 분리 후 옛 resum/·모노레포 문구 정리 (Claude)

- personal_ai_project 모노레포를 프로젝트별 저장소로 나눠 이 프로젝트가 `tabjun/job_agent` 루트가 되었다(job_agent/develop/main 이력 그대로, 커밋별 트리 일치 확인). 로컬 폴더는 `toy_agent_project/job_agent`, 미커밋 작업·개인 자료·.venv 패키지 구성은 그대로 옮겼다.
- 사용자 요청으로 AGENTS·CLAUDE·process·README·docs/public_hosting·배포 템플릿의 `resum/` 경로와 모노레포 공통 격리 규칙 언급을 저장소 루트 기준으로 고쳤다. 지난 이력 기록 속 resum 표기는 당시 사실이라 두었다.
- 작업 중이던 미커밋 변경과 섞이지 않도록 이 문구 수정만 커밋했다.

## 2026-10-12: 공고 알림 실사용 검증과 매칭 품질 보완 (Claude)

- 사용자 Gmail SMTP(앱 비밀번호)로 실제 검증: SMTP 로그인 → 인증 코드 메일 수신·사용자 직접 인증 → 5개 플랫폼 데이터/AI 전반 조건 저장 → 미리보기 → 실제 발송 `새 공고 30건 발송` 성공(로컬 UI, 보이는 Playwright 창). Tavily 실검색 사용.
- 실데이터에서 발견한 문제 보완: 영어·숫자 키워드(R/AI/ML) 단어 단위 일치, 같은 제목 다른 URL 중복 제거 및 보낸 제목 기억(`sent_titles`), 검색 목록 페이지(`총 N건의 검색결과`·직무별 채용 등) 제외, 지역 필터(`서울, 경기` 하위 도시 포함, 다른 지역만 명시된 공고 제외, 지역 미기재는 메일에 원문 확인 표시).
- 사용자 지역 선호(서울 전역 + 경기, 특히 성남/판교, 그 외 지역 제외)를 테스트 알림에 반영 후 미리보기 28건. 캐치 지난 마감(~MM/DD) 공고와 부트캠프 등은 아직 남을 수 있음.
- Git: develop 대비 job_agent 병합 시 quantitative_trading 731→0 파일이 되는 원인은 2026-10-06 `b05617b` merge revert 커밋. 사용자 요청으로 확인만, 변경 없음. 프로젝트별 저장소 분리는 stock 서버 경로 연동 때문에 보류.
- 검증: 알림 테스트 12개, 전체 126개 OK(4 opt-in skip). 커밋·푸시 없음.

## 2026-10-12: Codex 적대적 리뷰 반영 · 공고 알림 메일 추가 (Claude)

- `/codex:adversarial-review --base origin/develop` 결과 high 2건 확인. (1) 인증 공유 방문자가 `/api/sync`로 운영자 PC 포털 세션을 열고 입력·저장할 수 있던 문제를 수정: 모든 모드에서 로컬 소유자 + `X-Admin-Token`만 허용, 원격 화면의 사이트 저장 패널 숨김. 회귀 테스트 `test_shared_visitor_cannot_drive_portal_sessions` 추가. (2) `origin/develop...job_agent` diff에 quantitative_trading 719개·apple 파일 삭제가 포함됨을 확인. 브랜치 이력 문제라 코드 변경 없이 사용자 결정으로 보류(develop 승격 전 분리 필요).
- 공고 알림 기능 추가: `job_agent/alerts/`(이메일 6자리 코드 인증·해시 저장·재요청 제한, 플랫폼별 직무/지역/키워드/제외 조건, 매일/평일/매주 예약, 보낸 URL 재발송 방지, 놓친 발송 1회 보충, 실행 잠금), UI `공고 알림` 화면(`alerts.js`), `/api/alerts`(로컬 소유자+관리 토큰만), `job-agent alerts list|run --due|--id` CLI, `docs/job_alerts.md`. SMTP는 `.env` `ALERT_SMTP_*`, 검색은 기존 Tavily. 공유·공개 체험·Vercel에서는 차단.
- 신규 기능 대상 2차 적대적 리뷰(working-tree) 반영: 모든 상태 변경을 프로세스 간 파일 잠금(`.state.lock`)으로 직렬화·고유 임시파일 저장, 검색 후 발송 직전에 알림 존재·이메일 인증·설정 revision을 재검증(인증 해제/삭제/수정 시 발송 안 함), 예약 실행 중 개별 알림 오류가 나머지를 막지 않게 수정.
- 검증: 신규 `tests/test_job_alerts.py` 9개(경쟁 상황 2개 포함), `tests/test_job_alerts_browser.py` 1개(가짜 메일/검색으로 인증→조건 저장→미리보기, 390px 가로 스크롤 없음) 통과. 전체 `python -m unittest discover -s tests` 124개 OK(4 opt-in skip). Ruff는 신규 파일 기준 통과. 실제 SMTP 발송과 실제 Tavily 검색은 사용자 메일 설정 전이라 미실행. 커밋·푸시 없음.

## 2026-10-09: 전체 변경 커밋·푸시 준비

- 사용자 요청으로 공통 경로 보호 정책과 resum 기능/문서/테스트 변경을 별도 커밋으로 분리. 개인정보 자료·키·로그인 세션·생성 결과는 staging 제외. 합성 사용 예시 이미지 14개만 포함.
- 전체 unittest 113개 중 109개 통과·개인자료/공개 URL opt-in 4개 제외. isolation 9개 통과, uv lock --check, Ruff E9/F63/F7/F82, staged diff --check 및 경로 검사 통과.
- 브랜치 전환 시 tracked 훅/검사 파일이 사라지는 문제 보완: tools/isolation/install.py로 공통 Git 디렉토리 project-isolation에 검사를 설치하고 core.hooksPath 설정. 임시 저장소에서 원본 규칙 파일 제거 후 검사/타 프로젝트 차단 검증. 로컬 설치는 서버/다른 clone에 자동 전파되지 않음.
- 푸시 대상 origin/job_agent만 사용. stock/apple/develop/main 병합·승격 없음. GitHub 푸시와 Vercel 재배포는 별개이며 이번 요청은 Git 저장 대상.

## 2026-10-09: 사용자 요청으로 추가 worktree 제거

- 새 worktree의 변경/무시된 파일 확인: 생성된 동일 Git LFS 훅 4개씩 외 다른 변경 없음. git worktree remove로 toy-stock/toy-apple/toy-integration 제거 및 연결 작업 공간 파일/안내문 제거. 원래 root/자료/미커밋 이력서 변경과 프로젝트 브랜치는 보존.
- 단일 체크아웃에서 프로젝트별 명시 경로 staging/commit/명시 branch push, 작업 직렬화, 미커밋 상태 강제 전환 금지 정책으로 전환. 공통 커밋 훅은 유지, 커밋·푸시·병합 없음. stock 최신 ref는 dd316ef 유지.
- 검증: worktree list는 원래 job_agent 1개만 표시, 추가 폴더/진입 파일 없음 확인. isolation 테스트 8개 및 diff --check 통과. 현재 미커밋 변경은 그대로 보존되어 브랜치 전환 전 정리가 필요함.

## 2026-10-09: 프로젝트별 Git worktree 분리 (이후 취소)

- 기존 root/job_agent와 resum 미커밋 변경·자료·환경은 보존. 같은 Analysis 계층에 toy-stock(stock), toy-apple(apple), toy-integration(develop) linked worktree 생성. 각 프로젝트만 여는 .code-workspace 파일 4개와 toy-worktrees.md 생성.
- stock의 실제 서버 프로젝트 경로 quantitative_trading을 stock 소유 경로로 등록(legacy stock 경로도 유지). 새 stock worktree만 4673028→dd316ef로 15커밋 fast-forward pull; apple/develop 최신 확인. 원격 서버 변경·커밋·푸시·프로젝트간 병합 없음.
- 절대경로 공통 pre-commit으로 별도 worktree에서도 소유권 검사. stock 기존 notebook mirror/정책 훅 유지 및 생성 파일 재검사, Git LFS 훅 유지. apple의 기존 비활성 상세 정책은 그대로이며 공통 경로 보호는 적용.
- 검증: isolation unittest 8개 통과(실제 임시 linked worktree, 독립 index/dirty 원본 보존, 타 프로젝트 및 프로젝트 훅 생성 파일 커밋 차단). 새 stock/apple 실제 hook run 성공, diff --check 통과.
- .venv·키·무시된 데이터/결과는 복사하지 않고 원래 폴더 보존. 새 worktree 실행 환경 준비는 별도. Git LFS가 생성한 새 worktree 루트 .githooks 4개 파일은 미추적 상태로 보존; 스테이징하지 말 것. 공통 훅은 원래 root에 의존, 서버/다른 clone에 자동 설치 아님.

## 2026-10-08: Windows 더블클릭 연결 도구

- ZIP의 `Start-Resume-Connector.cmd`와 한국어 START-HERE/README 추가. uv가 없으면 공식 WinGet 설치를 직접 선택하도록 묻고 locked sync 실패 시 서버를 시작하지 않음. 보안 경고/실행 정책 우회·동의 자동 수락 없음.
- 런처: 정확한 origin 검증, Chrome/Edge 또는 전용 Chromium 준비, 기존 loopback 서버·포트 fallback·브라우저 자동 열기. 기존 작업 폴더 대신 새 압축 폴더 사용 안내.
- 웹 다운로드 시 현재 origin을 connector.json에 설정. 플랫폼 연결 화면/예시/README에 압축 풀기·더블클릭·창 유지·종료와 PowerShell 여는 방법 추가. 실제 EXE 배포나 모바일 단독 자동 저장으로 설명하지 않음.
- 검증: 런처 5개(Windows CMD 실제 실행/실패 차단은 uv stub, 추출 ZIP의 실제 개인 서버 시작), 플랫폼 연결 8개, 이미지 자산 3개, hosting 5개, 예시 브라우저 1개 총 22개 통과. uv lock --check, scoped Ruff, diff --check 통과. 새 PC에서 WinGet 신규 설치 자체는 실행하지 않음.
- `result/hosting/doubleclick-connector-release-20261008`만 고정 Vercel에 배포: `dpl_DsUwjApxmerqLQJZoqeUTM8tQW9k`. Codex 브라우저에서 실제 ZIP 다운로드 후 cmd/launcher/설정 파일 및 현재 origin 확인. 기존 사용자 환경/자료/포털 세션은 변경하지 않음.

## 2026-10-08: 직접 수행한 화면으로 사용 예시 보강

- Codex 내 브라우저에서 가상 공고 실행, 기술 항목 작성·검수, Word 빈 양식 다운로드, JD 정리와 플랫폼 선택, 공개 HTTPS→임시 로컬 가져오기 승인을 실제 수행해 14장 캡처.
- 로컬 테스트 양식에 소개를 실제 입력·저장하고 재접속 확인 성공. 실제 포털 계정 저장 검증과 구분해 사진별 설명에 명시.
- 서비스별 갤러리·확대 dialog·플랫폼 연결 예시 탭 추가. 로컬/공개/연결 ZIP의 이미지 배포는 명시 allowlist로 제한. 개인정보와 인증 정보 없음.
- 가상 테스트 서버 종료·임시 공간 정리. 기존 사용자 파일/로그인 세션/브랜치/인접 프로젝트는 변경하지 않음.
- 검증: 전체 `unittest discover -s tests -v` 105개 중 101개 통과·4개 opt-in 제외. 추가 `test_tutorial_assets` 3개, 공개 HTTPS `HostingHttpTests` 2개 통과. 390/1440px 모든 예시 이미지 로딩·확대/Escape·무자동저장 검증. Ruff E9/F63/F7/F82/I 및 `git diff --check` 통과(기존 broad-except lint 3개는 이번 범위 밖).
- 코드 전용 `result/hosting/tutorial-screens-release-20261008` 배포 완료: `dpl_29ZJAEz4cWvRHACqfvJNAC1qWuGH`, 고정 `https://job-agent-resume-web.vercel.app/#examples/profile`. Codex 브라우저에서 배포된 갤러리/확대/플랫폼 연결·저장 예시 확인. private backup ZIP은 업로드하지 않음.

## 2026-10-08: 플랫폼 전환·저장 중심화

- 5개 플랫폼 체크/진행, 웹→본인 PC 다중 선택 전달, 로컬 브라우저 열기·상태 확인/사이트별 저장 결과 표시. 회사 JSON 변환은 고급 접힘으로 보존.
- 로그인 세션은 사용자 PC persistent profile만 재사용. 쿠키 추출·공개 웹 세션 전달/원격 API 권한 부여 없음.
- 정확한 단일 항목명·길이·select 값 제안, 성공 연결 재사용, 단일 저장 버튼 제안. 저장 전 별도 승인/저장 뒤 readback 유지.
- 실제 정리 결과 선택 저장에 선택 프로필·공통 원본 digest 검증 추가. README/첫 안내/사용 예시 갱신.
- 검증: 전체 105개 테스트 중 101개 통과·4개 opt-in 제외. 최신 sync 7개(5개 사이트 경로 실제 테스트 DOM 저장/readback·persistent cookie 재사용 포함), 큐 UI 2개 통과. 공개 HTTPS hosting 5개와 웹→본인 PC 다중 선택/승인 전달 8개 통과. 실제 5개 포털 계정 저장 검증은 아님. 390/1440px 화면 확인, Ruff/whitespace 검사 통과.
- 개인 환경을 보존하고 코드 전용 `result/hosting/portal-workflow-release-20261008`만 고정 Vercel 주소에 배포. 성공 편집 URL은 로컬 연결 파일에만 보관·허용 사이트/편집 URL 재검증 후 재사용. 자동 제출/실제 사용자 이력서 수정/브랜치 병합/커밋·푸시 없음.

## 2026-10-08: 첫 사용 안내와 공개 메뉴 정리

- 기본 첫 탭 `처음 사용하기`: 목적, 독립 공고 탐색, 공통 작성→정리→검수→변환 연결과 단계별 이동 버튼 추가.
- 결과 기록·외부 공유 링크 메뉴/뷰/사용 예시 및 UI 조회 호출 제거. 공개 transport 이전 실행 Map/조회 삭제; 현재 결과와 공통 이력서만 RAM 유지. 기존 로컬 기록·CLI 공유는 보존.
- 공개 검색은 직접 입력, 회사 JSON 양식 준비와 PC 로그인/MFA/저장 범위 명시. 오래된 아키텍처 이미지를 구현 완료처럼 사용하지 않음.
- 검증: 전체 `unittest discover -s tests` 102개 통과(4개 opt-in 제외), 공개 HTTPS `test_hosting.py` 5개 통과, Ruff F401/F821 통과. 390/1440px 안내 화면 스크린샷 확인. 코드 전용 export `result/hosting/guide-navigation-20261008`만 배포; 고정 주소 `https://job-agent-resume-web.vercel.app`, deployment `dpl_649NvuEXaTby5G39XcsNH8Kqy4Uf`. 개인정보/키 업로드 및 브랜치 병합/커밋/푸시 없음.

# history.md

## 2026-10-08: 일반 사용자용 정형 이력서·Word 입력

- 사용자 지적에 따라 `documents/sections.py`의 경력/학력/기술/프로젝트/자격증/수상/어학/교육/활동/논문/특허/링크 단일 스키마와 반복 `items` 입력·추가·삭제 구현. 회사/직무/고용 형태/기간/재직 중, 자격번호/기관/취득일 등 세부 항목 분리. 원문 임의 분류 없이 기존 문자열 프로필과 CLI 호환 유지. 표시 텍스트 불일치·잘못된 날짜·재직 중 종료일·미검수/불완전 실행 차단.
- Word 기본 양식과 작성본 다운로드·업로드, 선택 Markdown/JSON을 브라우저 fflate 0.8.2(MIT)/XML로 구현. 숨은 JSON payload 없이 Word 표의 항목명으로 읽으며 일반 DOCX는 소개 원문으로 보존. 공개 서버 DOCX 추출 API/개인 모델/포털 작업 차단 유지. 업로드 후 검수 초기화, 공개 프로필은 탭 RAM 유지. 이력서 정리 결과는 레코드 단위로 정렬하고 명시 검수 후 회사 양식 변환 입력으로 선택, 원본은 보존. 사용 예시·README·입력 규격 갱신.
- knowledge 경력 DOCX와 취업 폴더의 공통 경력·경험·데이터 분석가·CV DOCX 및 이력서/지원서 PDF의 추출 가능한 항목 구조 참고. 텍스트 없는 PDF의 OCR/모든 자료 자율 분류는 수행하지 않음. 개인 내용은 양식·예시·공개 코드에 넣지 않음.
- 검증: 실제 private 경력 DOCX를 로컬 메모리 UI에서 가져오기/미검수/미저장 확인. 전체 `python -m unittest discover -s tests -q` 102 tests 실행, 실패 없음(3 skip: 별도 환경 미지정). 새 정형 회귀 6 tests(실제 DOCX 포함), Word/MD/JSON 레코드·줄바꿈·날짜 round-trip, 로컬/공개 export 입력·승인·정리→회사 선택·원본 보존·390/1440px 레이아웃·JS 오류/브라우저 자동 저장 없음 확인. API 거절 시 Windows unread body reset을 bounded read/timeout으로 수정, 호스팅 5 tests 통과. Ruff 검사 통과.
- DOCX 패키지 renderer는 LibreOffice 부재로 실행 불가. 설치된 Word의 읽기 전용 COM PDF 렌더와 bundled PDFium으로 빈 양식 6페이지/작성 예시 3페이지 전부 시각 검수, 표 분할·글자 겹침·잘림 없음 확인. 생성 QA 자료는 ignored result에만 보관. 기존 환경 private 백업 후 별도 code-only export로 동일 Vercel 고정 주소 배포 진행.
- 배포 완료: `https://job-agent-resume-web.vercel.app`, deployment `dpl_HgBgnRn1NQe4sredq4vyAodZWRKE`, allowlist export `result/hosting/structured-resume-20261008`. 실제 고정 HTTPS에서 정형 입력·Word/MD/JSON round-trip·모바일 레이아웃·정리→회사 입력 선택 1 browser test와 호스팅/권한 경계 5 tests 추가 통과. 실제 개인 DOCX는 localhost에서만 테스트했고 공개 HTTPS에는 가상 값만 사용. Git commit/push·프로젝트 브랜치 병합·유료 모델 호출·실제 포털 변경 없음.

## 2026-10-08: 루트 monorepo 프로젝트 격리

- 사용자 요청으로 root AGENTS, stock/apple AGENTS, `tools/isolation/` 소유권 manifest·staged/range 검사, `.githooks/pre-commit` 추가. stock→develop, apple→develop, job_agent→develop→main 흐름과 프로젝트별 worktree 규칙 명시. 다른 프로젝트/develop/main 역방향 병합 금지, root 정책 변경은 별도 governance-only 커밋.
- 기존 `core.hooksPath=quantitative_trading/.githooks`에 실행 훅이 없어 `.githooks`로 설정. 브랜치/업무 코드/기존 미커밋 변경/개인 자료 보존. 실제 merge/commit/push/worktree 생성 없음. 다른 브랜치/클론에는 규칙 파일 배포·훅 설치 필요; 충돌 0 보장이나 CI 강제 설정으로 설명하지 않음.
- 검증: 임시 Git 저장소 테스트 6개(브랜치 판별, 타 프로젝트/루트 차단, governance 범위, rename 양쪽 검사, 범위 검사, 독립 stock/apple develop 병합). `python -m unittest discover -s tools/isolation -p "test_*.py" -v`. 실제 현재 staged 검사 성공(0 paths), diff check 성공(CRLF 경고만).

## 2026-10-08

- 기존 로컬 UI·가상환경·개인 `.env`·이력서/결과/로그인 프로필을 보존하고 Vercel용 별도 export 추가(`job_agent/hosting/`, `deploy/vercel/`). 변경 전 소스·설정·의존성 및 `.env` 포함 private ZIP을 ignored `result/hosting/backups/`에 보관, `.env` 원본과 백업 동일 확인. 공개 export는 allowlist 코드·빈 표준 양식·코드 전용 연결 ZIP만 포함하며 개인 자료/키/세션 제외. Supabase와 유료 모델/검색은 연결하지 않음.
- 공개 UI 프로필/기록은 탭 RAM(새로고침 시 초기화), 실행 자료만 같은 Python 결정론적 워크플로우를 요청별 호출·finally 정리. same-origin JSON/2MB 제한, 개인 자원/포털 작업 차단, no dotenv/no 파일·DB·내용 로그. 기존 로컬 API에는 별도 transport가 없으므로 기존 동작 유지. 공개 안내·고정 링크 복사·own-PC 연결 안내·수동 GitHub CI 템플릿/배포 문서 추가.
- 모바일 승인으로 Vercel CLI 인증, 전역 CLI 63.1.0·Codex Vercel 플러그인 설치·global `https://mcp.vercel.com` 등록. MCP OAuth는 로컬 콜백 인증 미완료로 중단(CLI 배포 인증과 구분), 현재 세션 MCP list_teams 도구 검증 없음. Hobby 계정 확인, 원본 GitHub 저장소 자동 연결은 실패하여 자동배포는 미연결/CI 템플릿 미활성. 별도 allowlist export만 CLI 배포 완료, 고정 공개 주소 `https://job-agent-resume-web.vercel.app` 무인증 HTTP 200 확인. Cloudflare 서버/터널은 삭제·중지하지 않음.
- 최초 Vercel 빌드 오류는 imported handler만 있는 함수 파일의 정적 진입점 인식 때문. export의 `api/run.py`에 top-level handler class를 명시해 해결, AST 회귀 검사 추가. legacy builds 시도는 제거하고 최종은 표준 functions/public 설정 사용.
- 검증: 전체 `python -m unittest discover -s tests -q` 96 tests 성공(3 skip: 명시 외부 주소/개인 원문 환경 미지정), 호스팅 5 tests 실제 고정 HTTPS에서 별도 성공(`RESUME_HOSTING_TEST_URL` 지정): 정리 API 실행·공급자 조작 차단·교차 출처 차단·비공개 경로 404·표준 양식/작성본/코드 ZIP 다운로드·업로드 검수 해제·탭 격리·쿠키/자동 localStorage/sessionStorage 저장 없음·새로고침 초기화·390/1440px 화면/JS 오류 없음. 유료 호출/실계정 포털 변경 없음.
- 끊어진 세션 재개 후 실제 고정 HTTPS 호스팅 5 tests 재통과, 같은 Vercel origin에서 본인 PC 팝업의 전송 동의·로컬 승인·검수 해제·개인 저장 분리·계정 작업 미실행 연결 1 test 성공. Vercel 프로젝트 사용자 환경변수 0개 확인. 최종 소스/설정 private snapshot과 해시 manifest가 일치하는 새 code-only export 재생성·같은 고정 도메인으로 배포, 원본 보존 유지.

- 플랫폼 로그인/2차 인증을 이용자가 따라 할 수 있도록 플랫폼 연결 페이지·5개 대상 선택·본인 PC 실행/전달/인증/검수·저장 안내 추가. 코드 전용 다운로드 ZIP(개인 파일/키/브라우저 프로필 제외), `--handoff-origin` exact origin과 웹 전달 동의/로컬 가져오기 승인, request ID/opener/source/origin 확인 메시지 연결 구현. 이력서만 전달, 자동 저장/계정 정보/토큰 전송 없음. 전화만의 자동 로그인/회사 자체 사이트 자동 입력은 미지원으로 고지.
- `ResumeSync.status`로 로그인/MFA/보안 확인/편집 후보 상태 안내, 인증 화면의 수집·입력 차단. 읽기 전용 신호 확인이며 인증 성공을 보장하지 않는다. 실제 HTTPS→로컬 팝업의 same-origin 제한을 발견, 명시 handoff 설정의 root 최상위 탐색만 허용하고 교차 출처 API/POST는 계속 차단. 연결/ZIP 코드만 포함/새 폴더 CLI 도움말/권한 경계 8 tests, 인증 차단/기존 저장 fixture 6 tests 성공. 실제 사용자 계정 로그인/2FA/포털 변경은 수행하지 않음.
- 실제 DOCX/master 포함 전체 91 tests 성공(명시 외부 주소 테스트 1 skip), 실제 공개 HTTPS에서 연결/키트 다운로드/로컬 승인/검수 해제/파일 저장 분리/모바일·데스크톱 8 tests 별도 성공, 기존 메모리 공개 UI 외부 테스트 별도 성공. Ruff/diff 검사 통과. 새 공개 서버에 플랫폼 연결 안내 적용, 이전 터널 중지. 공개 페이지의 로그인 완료 오인 표시/자격 증명 수집/운영자 포털 접속 없음.

- 사용자 요청으로 공개 방문자 임시 디스크 저장을 세션 메모리 전용으로 변경. 기존 개인 로컬 파일 저장은 보존, 공개 프로필/결과는 서버 파일/DB/내용 로그에 기록하지 않음. 1시간 세션과 60초 만료 정리 thread·명시 삭제 endpoint/하단 버튼·최근 결과 상한, 다운로드로 사용자 기기 보관. 모델/검색/실제 포털 차단 유지. 개인정보 처리 안내를 최하단에 추가, 처리 항목·목적·메모리/로컬 구분·삭제·쿠키·Cloudflare·OS 스왑/덤프 한계를 설명하고 법적 준수 인증으로 단정하지 않음. 문의처 `RESUME_PRIVACY_CONTACT`, 실제 공개 연락처 질문 중.
- 메모리/개인 저장본 격리/무파일 쓰기/검수/명시 삭제/주기 만료 포함 9 tests 성공. 이전 공개 터널 중지; 이전 방식의 방문자 시험 파일 폴더 삭제 명령은 실행 정책 차단으로 미수행(운영자 기존 이력서 삭제 시도 없음). 새 메모리 서버·터널로 전환, 검증/주소는 별도 기록 없이 안내.
- 전체 실제 DOCX/master 포함 82 tests 성공(외부 주소 지정 테스트 1 skip), 새 HTTPS 외부 Playwright 테스트 별도 성공. 390/1440px 하단 개인정보 안내/삭제 버튼·표준 이력서 입력/임시 반영/내 기기 JSON 다운로드·세션별 결과·새로고침·localStorage/sessionStorage/IndexedDB 0·명시 삭제 후 이력서/결과/폼 빈 상태·다른 방문자 유지 확인. 화면 스크린샷 확인, JS 오류 없음·유료 호출/포털 변경 없음. Ruff/diff 검사 통과. 법적 준수 인증 문구는 넣지 않고 공개 문의처 미등록 상태를 명시했다.

- 접근 코드 UI 제거 요청: 공유 화면 코드 입력/표시/복사 요소 삭제, `--public-demo` 익명 브라우저별 격리 공간 추가. 외부 root 탐색에서 Secure/HttpOnly 세션 자동 생성, 기존 개인 공간·결과·포털 세션 접근 금지. 공개 모드의 운영자 모델/검색 자원 허용 병용 거부, DOCX 추출·실제 저장 차단, 8시간 만료/종료 정리·동시 32개 제한. 기존 개인 공유 인증은 유지.
- 검증: 실제 DOCX/master 포함 전체 80 tests 성공(명시 외부 주소 테스트 1 skip), 새 방문자 HTTP/만료/개인 저장본 격리 테스트 7개 별도 재검증 성공. 외부 주소 지정 Playwright 테스트 1개 별도 성공: 실제 HTTPS 모바일 390/데스크톱 1440px에서 무코드 직접 링크·코드/모델 문구 없음·예시 공고 실행·결과 격리·새로고침·실제 저장/DOCX UI 숨김·JS 오류 없음 확인. Ruff/diff 검사 통과. 새 공개 체험 터널 실행, 이전 개인 공유 터널 중지. 개인 키 호출·실제 계정 저장 없음; 임시 주소/세션은 추적 문서에 기록하지 않는다.

- 사용 예시 전용 페이지와 각 작업 화면의 도움말 아이콘 추가. 공통 이력서/공고 탐색/이력서 정리/회사 양식/사이트 저장/결과 기록/외부 공유 7개 주제, 가상 입력과 예상 결과·검수/저장 한계·서버 PC 로그인 안내 제공. 표준 빈 양식 다운로드, 내 이력서 열기, 가상 공고/JD 넣기 및 실제 작업 화면 이동 구현. 예시는 사용자 경력으로 등록하거나 실행·저장하지 않는다.
- 예시 탭 ARIA/좌우·Home/End 키 이동, `#examples/<topic>` 직접 링크·새로고침 복원 추가. 로그인 성공 시 reload로 fragment와 위치 유지(같은 fragment로 replace 시 로그인 문서에 머무르던 동작 수정). 외부 모델/과금 정보 숨김 및 서버 자원 차단은 유지.
- 검증: UI 브라우저 4 tests 통과, 새 예시 테스트에서 모든 주제 390/1440px 화면·도움말 연결·가상 입력·표준 양식 다운로드·키보드·새로고침·POST 0회 및 공통 입력 불변 확인. 실제 공개 HTTPS Chrome에서 코드 로그인→예시 직접 링크→입력/도움말 복귀, POST 0회·JS 오류 없음·모바일/데스크톱 스크린샷 확인. Ruff/diff 검사 통과, 개인정보 입력·사이트 저장·유료 호출 없음. 정적 UI 갱신으로 기존 공유 URL 유지.

- 사용자 요청으로 외부 처리 모드 선택창 자체와 `LLM 없음` 배지 제거. 기본 HTML은 모델 영역 숨김, 로컬 소유자 확인 후에만 표시. 외부의 화면 이동으로 다시 표시되지 않으며 연결 메뉴·결과 모델/토큰 지표·기록 공급자 이름도 숨김. 방문자는 작업 입력/결과만 사용하고 서버 CLI 자원 정책은 유지. 정적 UI 갱신으로 기존 URL에 즉시 반영. 설정 UI/원격 모의 입력·결과·화면 전환 테스트와 실제 공개 HTTPS 모바일에서 모드/모델명/과금 문구 없음 확인, 개인정보/유료 호출 없음.

- 사용자 재확인: 방문자 과금 동의로 운영자 키를 켜는 흐름 금지. 외부 페이지에 공급자 선택지가 초기 HTML에서 잠깐 보이는 여지를 제거하도록 `RemotePage` HTML parser 추가. 서버 허용 모델과 검색 옵션만 첫 응답에 포함하고 외부 과금 문구를 전송 동의로 교체(로컬 운영자 화면은 유지). 서버 CLI 명시 허용/추가 비용 플래그 외에는 개인 키 호출 차단 유지.
- 기본 HTML은 모델 없음/수동 공고만 포함하고 `app.js`가 서버의 허용 목록을 받은 뒤 선택지를 생성하도록 fail-closed 처리. 과금 동의 문구를 표준 UI에서도 제거하고 전송 동의만 유지. 실행 서버는 정적 파일 갱신으로 즉시 반영(추가 Python 렌더 필터는 다음 재시작에 로드), 기존 URL/접근 코드 유지. 실제 공개 HTML의 유료 선택지/과금 문구 없음, Chrome 모바일 visible text에 OpenAI/Gemini/과금 없음, ai_consent=true를 조작해도 두 공급자 요청 403 확인. sharing 12·parser 2·UI browser 2 tests 통과, Ruff/diff 검사 통과. 유료 호출 미실행.

- 사용자 정정: 외부 공유 화면에서 운영자 자원 ON/OFF를 변경하게 한 것은 의도와 다름. 정책 변경 UI/API와 소유자 코드/세션 권한 삭제, 기존 터널 중지 및 코드 폐기. `--remote-providers` 서버 실행 옵션으로만 허용 목록 지정, 기본 외부 LLM 없음만 허용. OpenAI/Gemini는 별도 `--allow-remote-paid-api` 없으면 시작 거부, 개인 Tavily도 기본 차단·`--allow-remote-web-search` 명시 시만 허용. 로컬 모델 사용은 유지. 공유 관련 12 tests로 정책 HTTP 변경 불가/기본 자원 호출 차단/명시 자체 허용/유료 실행 가드 검증.
- 최종 검증: 실제 DOCX/master 통합 포함 전체 68 tests 통과, Ruff/diff 검사 및 CLI help 확인. 비용 허용 없이 OpenAI 외부 지정 시 시작 거부(exit 2) 확인. 새 공개 HTTPS에서 선택지 LLM 없음만·관리 폼 없음·정책 변경 404·custom/OpenAI/Gemini 및 Tavily 직접 요청 403 확인, 유료 API 미호출. 이전 터널은 중지했고 새 서버는 기본 차단 정책으로 공유 중이다.

- 외부 모델 ON/OFF를 고정 제한에서 소유자 설정으로 변경. 공유 탭에 자체/OpenAI/Gemini 체크박스·과금 동의·저장, config 필터와 실행 서버 허용 정책 연동. 기본 유료 모델 OFF, LLM 없음 항상 ON, 메모리 설정·15초 원격 선택지 갱신. OFF로 진행 중 호출을 취소하지는 않는다.
- 별도 소유자 접근 코드/소유자 세션으로 휴대폰의 모델 공개 정책 관리 허용. 방문자 정책 변경과 원격 소유자의 키/주소/터널 변경은 차단, 공유 중지 시 두 종류 세션 폐기. 코드 원문은 로컬 화면에만 제공하고 로그/추적 문서에 넣지 않는다. 허용/차단/동의/권한/폐기 sharing 12 tests와 설정 UI ON/OFF·과금 동의·모바일 브라우저 테스트 통과.
- 최종 검증: 실제 DOCX/master 통합 포함 전체 68 tests 통과. 실제 공개 HTTPS에서 원격 소유자의 OpenAI ON→방문자 선택지 표시→OFF→선택지 제거와 일반 방문자의 관리 폼 숨김, 390px 화면 확인. 테스트 후 OpenAI/Gemini OFF로 복원, 유료 추론 미호출. Ruff F401/F821·diff 검사 통과. 이전 터널 중지 후 새 서버 공유만 활성화.

- 외부 테스트의 모델을 사용자 요청대로 LLM 없음/자체 LLM으로 제한. 원격 config에 허용 목록만 반환하고 개인 OpenAI/Gemini 모델 ID·키 설정 상태를 제외, UI 선택지 제거. 서버가 원격 `/api/run`의 비허용 provider를 호출 전 403 차단하며 로컬 모델 설정은 유지. 허용/차단·호출 미실행 회귀 포함 sharing 10 tests와 UI 브라우저 2 tests 통과. 실제 공개 HTTPS Chrome 로그인 후 선택지 none/custom만 확인, 직접 OpenAI/Gemini 요청 모두 403 확인. 자체 서버는 아직 미연결. 이전 공유 중지 후 수정 서버의 새 인증 터널 사용.

- 휴대폰에서 채팅의 공유 링크를 누를 때 `Same origin required` 오류 재현: 외부 최상위 GET 탐색의 `Sec-Fetch-Site: cross-site`까지 출처 검사로 차단한 원인. 활성 공유 host의 `/`·navigate·document 요청에 한해 로그인 화면만 허용하고, 쿠키가 있어도 이 경로에서는 개인정보 UI를 반환하지 않는다. API/POST/임베딩 요청의 기존 출처·인증·토큰 검사는 유지. 재현 회귀 포함 sharing 10 tests 및 Ruff 검사 통과. 수정 서버를 별도 포트로 기동해 새 임시 공유 주소를 사용한다. 실제 공개 HTTPS의 cross-site 요청 200/로그인 화면 및 API 403, 별도 Chrome에서 example.com 출처 링크 클릭→코드 로그인→REMOTE 화면 확인. 이전 터널은 중지했다.

- 사용자 요청으로 UI 자체 LLM 연결 추가: OpenAI 호환 기본 URL(IP/포트)·모델 ID/서버 등록 경로·선택 API 키, Ollama/LM Studio 프리셋, 모델 목록 조회와 실행별 자체 LLM 선택. `CustomModel`은 키/설정을 메모리에만 유지하고 별도 키를 사용하며 기본 결과 보존·단일 분석 호출 정책을 유지한다. 직접 모델 파일 로드나 기존 CLI 모델 교체는 아니다.
- `Sharing`으로 Cloudflare Quick Tunnel 수명·접근 코드·8시간 인증 세션·로그인 시도 제한을 캡슐화했다. UI 외부 공유 탭의 명시 동의/생성/중지/주소·코드 복사, HTTPS 원격 로그인 화면 추가. 인증 전 개인정보/API 차단, 로컬 소유자만 모델/공유 설정 변경, 중지/종료 시 세션 폐기. 단일 소유자 공유이며 다중 사용자 격리는 지원하지 않는다.
- 공식 cloudflared 실행 파일을 ignored `result/tools/`에 설치하고 별도 UI 서버에서 실제 공개 HTTPS 터널 실행. 무인증 로그인 화면 200/프로필 API 401 및 Playwright Chrome의 실제 코드 로그인·REMOTE 화면·390px 레이아웃 확인. 연결 Chrome 확장은 주소 차단으로 별도 headless Chrome 검증으로 대체. 주소/코드/증빙은 Git에 넣지 않는다.
- 검증: 실제 DOCX/검수 master 통합 포함 전체 65 tests 통과. 자체 모델 HTTP fixture·키 비노출·실패/동의·원격 인증/관리 경계·세션 폐기, UI 연결/모델 목록/클립보드/390·1440px 검증. 실제 보유 모델 가중치 추론/품질·유료 API 호출은 하지 않음. README에 자체 연결과 Windows/Linux 공유 실행법·개인정보/비용 권한·임시 주소 및 PC 실행 조건 기록. `uv lock`에 직접 httpx 의존성 반영.

- 외부 휴대폰 접속 사용자를 대신해 연결 Chrome에서 실계정 저장 확인. 원티드 연구 설명과 글자수 제한으로 잘린 AI 활용 문장을 보완하고 자동저장 후 reload/readback 일치. 인크루트 경력 섹션 저장 및 학력 연구 설명 중복 제거/저장 성공 알림, reload 후 경력·부서·연구 내용 일치 확인.
- 캐치는 제목·부서·경력 초안 readback은 일치하나 완성 저장은 확인되지 않음. 학력 주간/야간·학점/만점 근거가 없어 사용자 질문, 임의 보완 없음. 잡코리아·사람인은 현재 Chrome 세션에서 로그인 필요로 저장 미실행. 지원/공개 설정/동의/연락처 변경 없음. 개인정보 증빙/백업/결과는 ignored `result/site_sync/live-2026-10-08/`, 범위는 `docs/resume_authoring.md`에 기록. UI 전용 Python 프로필의 E2E 검증과 구분, 유료 API 미호출.

- 사용자 요청에 따라 표준 JSON 빈 양식 다운로드/작성본 업로드·다운로드를 명확화하고 UI의 사이트 업데이트·저장 흐름 추가. `ResumeSync`가 전용 Playwright 로그인 프로필, 기존 편집 화면 수집, 명시 항목 연결/저장 동작 승인, 입력·저장·재접속 readback을 캡슐화한다. `SyncWorker`는 HTTP 요청 간 같은 이벤트 루프에서 브라우저 수명을 유지한다.
- 저장 전용 버튼 whitelist와 원티드 자동저장만 허용, 목록/로그인/지원 화면·공개 설정·동의·작성완료/제출 제외. 현재 원문 digest·페이지·필드·버튼 재검증, 중복 실행 토큰 소비, native select의 정확한 label/value 변환, 기존 값/적용값 백업 및 저장 불확실 시 자동 재시도 없음. 확인된 연결/실행 기록은 ignored `result/site_sync/`에만 저장한다.
- 사용자 요청으로 UI 명시 검수/동의 후 기존 이력서 저장을 허용하도록 AGENTS/README/process/입력 규격을 정합화했다. 기존 CLI 저장은 수동이며 반복 항목/custom 위젯/회사 자체 URL 저장은 범위 밖이다. 5개 포털 연결은 실제 DOM을 사용하지만 실포털 저장의 종단 검증은 아직 남아 있다.
- 검증: 실제 DOCX/master 통합을 포함한 전체 51 tests 통과. 로컬 Chromium/HTTP fixture에서 버튼 저장과 blur 자동저장 후 재접속 유지, 저장 불확실/중복·오래된 승인/변경 DOM 차단, 백업, 지원 미실행 검증. UI는 표준 양식 다운로드·업로드와 모의 저장 요청·390/1440 화면 검증. Ruff F401/F821 및 diff 검사 통과. 유료 API/실계정 저장 미실행, UI 서버 재시작 후 빈 표준 14개 항목 반환 확인.

- 단일 입력 형식 `job-agent.resume/v1`/`ResumeProfile` 추가: 고유 필드 ID·원문·근거·검수 상태 검사와 기존 package 변환을 캡슐화했다. UI 공통 이력서에서 JSON/DOCX 가져오기, 항목 편집, 근거 열람, 저장·검수·다운로드를 수행하고 서류 정리/회사 양식 변환이 같은 저장본을 사용한다. 기존 CLI 입력은 호환 유지, AI 결과 자동 덮어쓰기 없음.
- 변경된 값/근거의 검수 승인을 서버에서 해제하고 미검수 값 실행을 차단한다. DOCX는 선택한 항목에 원문만 가져오며 사실/회사/기간 자동 분류를 하지 않는다. 내부 표준 규격과 반복 항목 경로·한계를 `docs/resume_input.md` 및 README/process/AGENTS에 기록했다.
- 이전 명시 선택 DOCX 6개의 해시와 원문을 재검증하고 검수 draft 컴파일 결과가 master와 일치함을 확인한 뒤, 8개 검수 필드를 ignored `result/resume_profile/profile.json`으로 이전했다. 로컬 출처 목록도 보존했다. 취업 폴더 전체를 새로 파싱한 것은 아니다.
- 검증: 실제 공통 입력으로 LLM 없이 2회 실행하여 동일 결과/원문 61개 문단 보존 확인. 실제 DOCX/master 통합 및 공통 입력 CRUD·검수 해제·버전/타입/중복 검사·회사 변환·토큰 보호·Playwright UI/다운로드/모바일을 포함한 전체 46 tests 통과. Ruff F401/F821와 diff 검사 통과. 유료 API 호출/실사이트 저장은 수행하지 않았다. 최신 UI 서버 재시작 및 저장본 8개 항목/미검수 0개 불러오기 확인.

- 로컬 UI 추가: `job-agent ui`로 모델 없음/OpenAI/Gemini 선택, 공고 JSON 또는 동의한 Tavily 검색, DOCX 원문 문단 정리, 기존 회사 양식 변환, 결과 비교·기록·JSON 다운로드 제공. 공개기관 연동은 보류하며 실제 포털 입력/저장/제출은 UI에서 실행하지 않는다.
- UI의 기본 처리는 LLM 없이 수행하고 AI는 같은 입력의 결과를 한 번 분석한다. 실행별 모델 선택/명시 전송 동의, 토큰·시간 표시, 실패 시 기본 결과 보존 및 자동 재시도 없음. 키는 화면에 노출하지 않고 결과는 ignored `result/ui_runs/`에 저장한다.
- loopback 전용 서버, Host/Origin/세션 토큰 검사, 정적 파일 whitelist 및 개인정보 파일 접근 차단 추가. Lucide 아이콘/라이선스 로컬 포함, 패키지 빌드에 UI 파일 포함. README에 PowerShell/Linux 및 VS Code·uv 빠른 실행법 기록.
- 검증: 실제 로컬 DOCX/master 통합을 포함한 unittest 41개 통과, Playwright에서 공고·모의 AI·DOCX·양식 변환·기록·다운로드와 390/768/1440 화면 검증. Ruff F401/F821, wheel/sdist 빌드 및 `uv run job-agent ui --help` 확인. 유료 AI/검색 실호출이나 모델 품질 평가를 수행한 것은 아니다.
- OneDrive 가상환경의 패키지 메타데이터 읽기 전용 속성으로 발생한 uv 설치 실패를 해당 로컬 메타데이터의 속성 정리 후 복구하고 `uv sync --extra browser` 성공을 확인했다. 다른 프로젝트/브랜치는 수정하거나 병합하지 않았다.

- Agent 1 외부 사례 조사: 사용자 지정 4개와 추가 3개 저장소의 관련 구현/명세를 커밋 고정 정적 검토. JobSpy/Oink 공개 설명 및 공식 서비스 6개, 공개 ATS/OpenDART 문서 추가 조사. 외부 실행·유료 사용·개인자료 전송·코드 복사는 하지 않음.
- `docs/agent1_landscape_2026-10-08.md`에 비교, 코드상 주의점, 라이선스 범위, 근거 기반 국내 지원 의사결정 리포트, P0~P3 도입/검증 기준 기록. README의 Agent 1 확장 목표와 현재 한계를 분리해서 반영. 기능 구현 완료를 주장하지 않음.
- 외부 스냅샷은 ignored `result/research/2026-10-08/`에만 보관. `job_agent` 브랜치 유지, 다른 프로젝트 수정/병합 없음. 검증은 문서/경로 및 diff 검사 범위이며 외부 테스트나 모델 성능을 재현하지 않음.

## 2026-10-07

- 회사 자체 채용사이트 확장: `SiteRegistry`로 사용자 등록 URL/명시 origin을 캡슐화하고 기존 고정 사이트는 유지. `target-register`, `application-prepare` CLI와 `--target` DOM 수집/입력 흐름 추가.
- `ApplicationAdapter`가 양식 schema, 공통 master 연결 후보/검수 bindings, 근거 보존 package, 미작성·미지원 필드 목록을 생성. 폼 digest 변경 및 근거 없는 필드 차단, 글자수 초과 경고(자동 절단 없음), native select label→value 변환. 모든 입력은 개별 승인 필요, 저장/제출은 수동.
- 가상의 미등록 회사 폼에서 실제 로컬 Chromium 수집→변환→입력→readback/제출 미실행 검증 및 origin 경계/양식 변경/근거/제한 테스트 추가. 실제 회사 사이트나 유료 LLM에는 요청하지 않음.
- 검증: 실제 DOCX/master 통합 환경변수로 전체 29 tests 통과(누락/skip 없음). Ruff F401/F821 및 `git diff --check` 통과. `job_agent` 브랜치 유지, 다른 프로젝트 병합 없음.

- 사용자 지정 모델 정책 갱신: 공식 OpenAI 문서에서 `gpt-6-luna`와 도구 호출 호환 조건을 확인해 OpenAI 기본값을 Luna로 변경했다. `OPENAI_MODEL`로 변경 가능. 추론을 유지하는 Responses API/medium 경로로 전환하고 sampling 파라미터는 제거했다. Responses 저장 비활성화 및 암호화 추론 상태 재전달, 콘텐츠 블록의 `.text` 표시를 적용했다.
- README와 3개 에이전트 모델 선택 안내를 정합화했다. 이전 `gpt-5-mini` 실호출 기록과 Luna의 모의 API 검증을 구분했다. 모델 기본값/재정의/SDK 직렬화/도구 실행/암호화 상태 재전달/텍스트 출력 회귀 테스트를 추가했다. 전체 22 tests와 Ruff F401/F821 검사 통과. OpenAI에 개인자료 전송이나 유료 실호출은 수행하지 않았다.

- 사용자 요청에 따라 루트 Python 파일을 `job_agent/` 패키지의 core/agents/documents/browser/sites/examples로 분리. 문서 근거, 브라우저 세션 및 검수 입력 계획을 상태를 가진 클래스로 캡슐화하고, 공통 경로/결과 저장 경계를 추가했다. 루트 지침 Markdown과 개인자료·결과·로그인 프로필 위치는 유지했다.
- `python -m job_agent` 및 설치형 `job-agent` CLI로 8개 워크플로우 진입점을 통합. 지연 import로 도움말/문서 처리에서 LLM을 실행하지 않는다. 상대 경로는 프로젝트 루트 기준이며, 기존 루트 파일 직접 실행 명령은 교체했다.
- 구조 회귀 검증: 실제 DOCX와 검수 master 포함 19 tests 통과, 기존 master JSON/Markdown 및 5개 사이트 패키지 재컴파일 결과 동일. Ruff F401/F821 검사 통과. 실제 계정 초안은 변경하지 않았다.
- 안티그래비티 프로젝트 설정 참조 제거. 빈 `.antigravitycli/` 물리 폴더 삭제는 실행 정책에서 차단되어 남아 있으며, 전역 앱은 변경하지 않았다.

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
## 2026-10-15: 공식 채용 알림과 요약 메일 구분

- 사용자 의도 정정: 각 사이트 계정의 조건/공식 이메일 알림 설정이 우선이며 프로젝트 SMTP 요약은 별도 경로. UI와 README/알림 문서에 두 경로 구분, 공식 사이트 계정 링크 추가. 계정 이메일/일반 광고/이력서 공개는 조작하지 않음.
- 요약 메일은 회사명·직무·공고 기간 3열 HTML + 텍스트 대체 본문. 직무 원문 링크, 플랫폼 작은 표기, 긴 요약/키워드/지역 반복 제거. 명시 기업/기간만 사용하고 미확인은 원문 확인. HTML escaping/안전 URL/인증메일 plain text 유지, 중복 발송/인증·잠금 정책 보존.
- 검증: 신규 메일 5개, 기존 알림 11개, 알림 UI 브라우저 1개 통과. 가상 메일 390/1280px overflow/3열/스크린샷 확인. scoped Ruff/diff --check 통과. 실제 SMTP/Tavily 발송은 이번 변경에서 실행하지 않음.
- 사용자 승인으로 전용 사이트 창 5개를 열었으나 사용자가 로그인 창 문제를 보고해 공식 설정은 미완료. 도우미 정리 후 Chrome 확장/@Chrome 연결 대안 안내. 비밀번호·OTP·쿠키 공유 요청/보안 우회 없음. 기존 다른 미커밋 작업 보존, 커밋·푸시 없음.

## 2026-10-15: Chrome 공식 맞춤 채용 이메일 실제 설정

- 사용자가 제시한 취업 Chrome 창을 연결 목록과 대조(확장 표시 이름과 사용자 프로필 명칭 차이). 기존 이메일 및 일반 광고 수신 항목은 변경하지 않음.
- 캐치 추천 채용 뉴스레터만 ON, 잡코리아 AI추천 메일 ON, 원티드 이메일 추천 포지션 ON. 캐치·잡코리아의 추가 개인정보 동의는 내용을 제시하고 사용자의 명시 승인 후 처리. 새로고침 readback으로 확인; 세 사이트의 상세 직무·지역·경력 이메일 필터 적용은 미확인, 추천/이력서/활동 기반 채널과 검색 필터를 구분.
- 사람인 서울·경기 전체 + 데이터분석가/데이터 사이언티스트/머신러닝/AI/통계·분석 + 신입/경력무관/1~5년 검색메일 구독 성공. 새 탭 저장 목록에서 수신 상태 재확인. 이번 턴 먼저 만든 경력 제한 없는 조건은 수신 취소하고 기존 구독은 유지.
- 인크루트 본인 2단계 인증은 사용자 직접 완료. 기존 별도 마이핏을 AI/데이터분석/빅데이터/머신러닝/통계·SAS, 서울·경기 전지역, 신입/5년 이하/경력무관으로 수정·저장. 새로고침 메일수신중 및 정보수신설정 ON 확인, 광고 OFF 유지.
- 실제 UI 증빙은 ignored result/job_alerts/live-2026-10-15/에 보관. 실제 받은 메일/발송 시점은 미검증. 코드 변경·커밋·푸시 없음, 이전 미커밋 작업 보존.

## 2026-10-15: 프로젝트 코드 리뷰와 흰 바탕 UI

- 사용자 후속 요청으로 완료된 작업 줄기/변경 묶음마다 검증 후 커밋·푸시하는 종료 규칙을 AGENTS.md/process.md에 반영. 이번 완료 변경(공고 알림 및 UI/리뷰/운영 기록)을 검토하고 `job_agent` 원격 동기화 대상으로 정리.
- 사용자 요청으로 주요 UI/API·공개 실행 경계·이력서 검수/저장·검색/알림·공용 엔진을 검토. `docs/code_review_2026-10-15.md`에 수정한 문제, 재현된 남은 문제와 구조 개선 제안 기록.
- 녹색 중심 팔레트를 흰 바탕·중립 회색·남색 브랜드·인디고 강조로 교체. 안내/모드/입력/결과/이력서 항목/플랫폼/알림을 카드로 구분하고 모바일 한 열 배치·키보드 포커스·메뉴 aria-current 보강. CSS 규칙을 줄별로 정리. 최초 안내 이미지 새 디자인으로 갱신, 기존 가상 기능 시연 이미지는 이전 디자인 안내로 보존.
- SMTP 보안 설정 정규화 및 ssl/starttls 외 값 연결 전 차단. 모의 테스트로 잘못된 보안 값의 네트워크 미접속, STARTTLS 선행, SSL 연결 확인.
- 제목만으로 다른 기업/별도 공고를 누락시키던 필터 제거. URL 기반 중복 처리와 최근 1000개 발송 기억 유지. 같은 제목의 A/B기업·A 별도 공고·후속 C기업 보존 및 동일 URL 재발송 방지 검증. 다른 주소의 같은 공고는 중복될 수 있음을 알림 문서에 반영.
- 남은 리뷰 항목: 일반 검색의 AI/R 부분 문자열 오탐(가상 email career에서 재현), 미등록 도구 호출의 ToolMessage 누락(모의 엔진 재현). 이번 변경은 이 두 경로를 수정하지 않았으며 다음 개선 후보로 문서화.
- 검증: `.venv/Scripts/python.exe -m unittest discover -s tests` 135개, 실패 없음/4개 skip. `test_*browser.py` 8개, 실패 없음/2개 skip. 메일 8개·알림 12개 및 튜토리얼 에셋 3개 통과. `uvx ruff check job_agent/alerts/service.py tests/test_alert_mail.py tests/test_job_alerts.py`, `git diff --check` 통과.
- 가상 임시 작업 공간에서 7개 화면 × 1440/390px 스크린샷 14개, 가로 넘침·JS 오류 없음. ignored `result/ui_review/white-2026-10-15/`에 증빙. 실제 SMTP/Tavily/채용사이트 변경·공개 배포·커밋·푸시 없음. 기존 미커밋 변경 보존.

## 2026-10-15: 글자 크기 확대와 첫 사용 흐름 도식

- 기본 글자 14→16px, 입력/라벨 16px, 안내 본문 16px 및 넉넉한 줄 간격으로 가독성 개선. 작은 보조 글자·메뉴·버튼·제목도 함께 확대하고 모바일 메뉴는 13px 유지. 알림 설정의 긴 환경변수 안내는 줄바꿈 처리.
- 처음 사용하기 상단에 기능별 SVG 아이콘과 화살표를 연결한 5단계 도식 추가: 공통 이력서 → 직무 맞춤 정리 → 플랫폼 전환 → 로그인·검수 → 저장·재확인. 클릭하면 기존 화면으로 이동하며 입력·저장을 자동 실행하지 않음. 좁은 화면에서는 세로 도식. 공고 탐색은 독립 기능으로 표시.
- guide-overview 안내 이미지 갱신. 기존 테스트의 중복 action 선택자를 사용자에게 보이는 버튼 이름으로 명확히 수정.
- 검증: UI 브라우저 4개(최초 선택자 오류 수정 후 해당 예시 테스트 재실행 통과), 알림 브라우저1, hosting5, 튜토리얼 에셋3 통과. 가상 임시 공간 7화면 × 1440/1024/768/390/320px, 아이콘 5개·각 단계 이동·가로 넘침/JS 오류 없음. 증빙은 ignored result/ui_review/readability-2026-10-15/.
- `git diff --check`와 예시 테스트 Ruff 통과. hosting 테스트의 기존 Ruff 경고 3개는 HEAD 원본에도 동일하며 이 작업에서 변경하지 않음. 완료 묶음은 job_agent에서 커밋·푸시하며 공개 배포·실제 포털/API/SMTP 실행 없음.

## 2026-10-15: README 접속 주소와 최신 화면 안내

- 사용자 요청으로 README 상단에 고정 공개 주소, 사용 예시, 로컬 기본 주소와 PC 연결 도구 링크 추가. 최신 흰 바탕/큰 글자/5단계 아이콘 도식 및 저장소의 안내 이미지 소개.
- 공개 주소 HTTPS GET HTTP 200 확인, 최신 도식은 아직 공개 배포되지 않은 상태도 구분. 실제 접속 포트·본인 PC 연결·승인 저장 조건 유지.
- 문서 링크 대상/이미지 경로 및 git diff --check 확인. 문서만 수정하여 기능 테스트는 재실행하지 않음. job_agent에서 커밋·푸시하며 공개 배포는 수행하지 않음.

## 2026-10-15: 공개 UI 배포 누락 수정

- 사용자 제보를 공개 HTTPS 재현으로 확인: 저장소에는 도식/새 CSS가 있지만 프로덕션에는 둘 다 없음. 캐시 회피 쿼리로도 재현되어 커밋·푸시 후 별도 배포 누락이 원인으로 확인됨.
- `hosting.build`로 새 ignored result/hosting/ui-refresh-4909bd8/에 코드 전용 export. 54파일/ZIP 경로 검수 및 Vercel dry-run에서 .env.local·.vercel 제외 확인. 원본/개인 백업/세션 업로드 없이 기존 taejun2/job-agent-resume-web에 production 배포.
- READY dpl_57U9vdCQ32RPa8RZoHe6ez5KYuVz, 고정 https://job-agent-resume-web.vercel.app 별칭 반영. 실제 HTTPS HTML/CSS/app.js SHA256이 export와 일치. /api/run 가상 수동 공고 HTTP200, OpenAI 요청400 차단 확인.
- 공개 주소 1440/390px 실제 브라우저에서 흰 바탕·본문16px·SVG아이콘5개·도식 단계 이동·예시 공고 실행·새로고침 결과 정리·local/sessionStorage 비사용·가로 넘침/JS 오류 없음 확인. 개인 자료·포털 로그인/저장·유료 API·메일 발송은 실행하지 않음. 증빙 ignored result/ui_review/production-2026-10-15/.
- README의 미배포 안내를 실제 배포 상태로 갱신. 공개 화면 완료 기준을 process.md에 기록. 문서 검증 후 job_agent 커밋·푸시.

## 2026-10-15: 확정 서비스 변경 즉시 배포 원칙

- 사용자 명시 지시: 서비스 변경을 확정해 커밋·푸시하면 별도 요청 없이 즉시 allowlist 배포·공개 주소 검증까지 진행. AGENTS.md/process.md에 강제 종료 절차로 반영. 문서만 변경해 배포본이 같으면 재배포는 불필요하며 실제 Git 자동배포 연동과 구분.
- 이번 변경은 운영 지침/기록만 수정. git diff --check 확인, 기능 변경/재배포 없음. job_agent 커밋·푸시.

## 2026-10-15: 공고 탐색 품질 재현·원문 수집 보강

- 사용자 불만을 조사: 기존 UI 5개 도메인 합산12건 상한, 직무/지역/기술/연도 몰아넣은 검색어, 목록·다른 서비스·마감·중복 혼입, 기업명 누락, 소수 모의 입력 위주의 테스트가 원인. 가상50건 중12건 재현 후50건 유지로 수정. 실제 기존혼합검색10건(기업표기3), 같은 검색어 사이트별60건 등 단계별 근거를 ignored result/search_quality/에 보관.
- 잡코리아·사람인 공개 HTML 검색 카드 우선 수집 추가. 기업/제목 카드별 연결·광고 관련도 검사, 미지원/차단/레이아웃 실패는 Tavily 색인으로 대체. 쿠키/로그인/스크립트/내부 API/보안 우회 없음. 동일 키워드 직접 검색에서 관찰한 퍼플아카데미·빗썸·티엠씨케이·메가스터디교육 등이 실제 원문 수집에 포함됨. 2사이트 원문 표본30→지역제외1→29건, 회사명 미확인0. 5사이트 전체 재현율은 미측정.
- 공용 postings 규칙으로 사이트별20건/최대3검색어(추가 대안 OR 보존), UI후보300/표시100, URL ID 정규화, 명시 마감·목록·별도 서비스 제거, 영어단어 오탐/기업·부서 혼동 감소. 한 기업·사이트 쏠림 완화. 기존 알림 조건·30건 상한·이메일/수신 설정은 그대로 두고 검색 계획만 개선. 검색 API 요청 최대15회로 증가 가능함을 안내.
- UI에 기업명 표기·원문/색인 출처·수집 수·직접 사이트 비교 링크, 알림에 수집/조건통과/선택/키워드근거부족 진단 및 메일상한 안내. 공개 Vercel은 수동 입력 정리만 허용하는 정책 유지.
- Agent 1의 별도 고정 직무/2026년5월/인크루트 누락/본문 마감 단어 무조건 제외 경로를 공통 수집기로 통합. 경력 요청은 보존하되 experience_verified=False로 표시. 원문 없는 경력조건 충족을 주장하지 않음.
- 새 test_search_quality12, test_native_jobs5, test_job_hunter_search1, 알림회귀2 추가. 전체154 tests 실패없음/4skip 및 추가 Agent1 테스트1 통과. 최종 원문5/검색12/알림14/메일8 재실행 통과, 브라우저8 실패없음/2skip. 기록 재생 UI 1440/390px 회사/출처/JS·넘침 확인 통과. 새 모듈/테스트 scoped Ruff, diff --check 통과(기존 다른 함수의 lint는 별도).
- docs/search_quality.md에 실측·한계·원문기준 품질 측정 절차, 감사 CLI --live/--replay 기록. API 예산을 제한한 실제 공고 조회만 수행했고 메일/LLM/포털 계정 변경 없음. 코드 전용 export를 준비하며 커밋·푸시 후 기존 Vercel 배포·고정주소 확인을 이어서 수행.
- 배포 완료: 기능 커밋 ee3c9c9 푸시 직후 result/hosting/search-quality-final-20261015/ allowlist 56파일 dry-run(.env.local/.vercel 제외) 검수, Vercel READY dpl_9eWnXwFTBNJs6QfVaqBgWwM5WBjp. 고정 HTTPS의 HTML/CSS/app.js/alerts.js/PC연결ZIP 해시 일치, ZIP native_jobs 포함/비밀경로 제외 확인. 실제 API 기업명·영어경계·공개web검색400 차단 및 1440/390px 공개 UI 회사명·비교링크5개·JS/넘침 확인 통과. 문서에 실제 배포 결과 기록 후 추가 푸시.

## 2026-10-20: 경력 포트폴리오 v4 개편과 공개 기록 정리 (Claude)

- 사용자 피드백으로 경력 포트폴리오를 흰 바탕·남색 한 색·키워드 제목 레이아웃(v4, 22장)으로 다시 만들고, 제출 문서의 프로젝트를 간접명으로만 쓰도록 바꿨다. 작업은 비공개 resum_summary(`6c6db7a`)와 로컬 취업 폴더에서 했고 job_agent 코드는 바꾸지 않았다.
- 사용자 요청으로 conversation_l2_cache.md의 식별 정보(회사 내부 코드명·계정·메일 주소)를 지우고, 해당 문구가 들어간 최신 커밋을 다시 만들어 job_agent에 강제 push했다(`3be9ee0` → `f235f05`, develop·main 영향 없음). AGENTS.md에 공개 문서 표기 규칙을 추가했다.
- 검증: 결과물(PPTX·PDF·HTML·JSON·MD·Word) 코드명 자동 검사 0건, 쪽수(이력서 3·경력기술서 10·포트폴리오 22·합본 32) 확인, PDF 렌더링 육안 확인. job_agent는 문서만 바뀌어 테스트와 재배포는 하지 않았다.


## 2026-10-20: 마감 공고 메일 혼입 재현과 발송 전 원문 확인

- 7월 공고/기간 지난 공고가 테스트 메일에 포함됐다는 제보. 실제 발송 이력과 재검색에서 제보 직무의 캐치 링크 확인. Gmail 본문은 재인증 필요로 읽지 못함. 공개 잡코리아 동종 직무 원문은 7월 17일 마감 표기 확인.
- collect 경계에서 지난 접수기간/괄호 마감일이 후보로 통과하는 2실패 재현. 표에 접수기간을 표시하면서 판정에는 읽지 않았고, 단독 마감 문구도 누락. 공통 날짜/상태 파서 보강, 게시일과 접수 마감 분리.
- core/job_status.py로 알려진 5플랫폼 공개 상세 URL만 제한 조회. JSON-LD/명시 기간·마감일/접수 라벨의 상시 모집을 확인, 마감 우선·미확인 보류·한국 시간 비교·발송 직전 재검사. 쿠키·로그인·내부 API·차단 우회 없음. 검색 후보 순으로 최대100개/4동시/8개 묶음, 메일 상한 도달 시 중단. 보류 URL은 발송 이력에 넣지 않음. UI/메일에 보류·마감 진단 추가.
- 실제 검색 응답266개 재생+최종 원문72개 점검: 검색단계 마감30, 상세 마감24, 상태 미확인17, 진행 근거30개 선택. 후보 기준 제외 수이며 전체 재현율 아님. 기존 알림 파일 해시 동일, 실제 메일/계정 설정 변경 없음. 원시 응답·상태 점검은 ignored result/search_quality/deadlines-20261020/에만 저장.
- 검증: `python -m unittest discover -s tests -p 'test_*.py'` 172개 실패0/4skip. 최종 직무/메일/마감 묶음33개, 검색12개, 메일8개 통과. 마지막 상시 모집 라벨 보강 후 상태10개 재실행 통과. 새 테스트가 기간 내 시각 추출 오류도 잡아 수정함. scoped Ruff와 diff --check 통과. 메일 브라우저는 가상 검색·원문·SMTP만 사용. 코드 전용 export/ZIP 원본 일치와 56파일 업로드 목록에서 개인정보/환경/세션 제외 확인.
- 완료: 기능 커밋 b32f0c8을 job_agent에 푸시한 뒤 allowlist 56파일로 기존 공개 프로젝트에 배포. 고정 https://job-agent-resume-web.vercel.app 의 HTML/CSS/app.js/alerts.js/PC연결ZIP HTTPS 해시가 최종 export와 일치하고, ZIP 안의 마감 검증/알림 소스가 저장소와 일치함을 확인. 실제 수동 검색 API200·운영자 web검색400 차단, 1440/390px 실제 브라우저 예시2건·가로 넘침/JS오류 없음 확인. 개인정보/키/세션 업로드·실제 메일 발송 없음. 로컬 운영자 알림은 로컬 코드에서 실행하며 공개 웹에서는 계속 차단됨.

## 2026-10-20 저녁: 마감 공고 메일 수정 후속 커밋과 이력서 지표 표현 (Claude)

- 사용자 확인: 미커밋 job_agent 코드는 공고 알림 메일에 접수 기간이 지난 공고가 섞이는 버그를 고치려던 후속 작업. 사용자 요청으로 전부 커밋·푸시.
- 포함 내용: 상세 원문의 제목 위치·지원 버튼·근무지·경력 추출(`core/job_status.py`), 직무·지역·경력·지원 가능 여부 판정과 플랫폼 간 중복 병합(`core/job_match.py`), 알림 `collect`의 요건 확인, 잡코리아·사람인·인크루트 원문 검색 보강, 웹 가입형 알림 초안(`alerts/cloud.py`, `hosting/alert_handler.py`, `deploy/alerts/*.sql`, `job-alerts.html`·`subscription.*`), 검색 평가 예제. `deploy/vercel/render.js`·`package.json`·`browser/public_snapshot.js`·`core/public_browser.py`는 아직 빌드·배포에 연결되지 않은 초안.
- Claude 리뷰로 고친 회귀: 제목 뒤 본문만 마감 문구를 보던 부분 때문에 제목 위의 '마감된 공고' 표시나 메타 설명에만 있는 제목에서 마감 공고가 모집 중으로 판정될 수 있었다. 제목 앞 영역도 마감 문구를 확인하고, 제목은 화면 본문에서만 찾으며, `div` 제목의 추천 공고 영역도 다시 잘라낸다. 경력 값이 `None`일 때 `collect` 전체가 멈추던 부분도 고쳤다. 회귀 테스트 3건 추가.
- 리뷰에서 남긴 주의점(미수정): 기존 저장 알림에 경력 기본값(1~5년/신입)과 활성 지원 버튼 요건이 새로 적용돼 메일 건수가 줄 수 있음, 키워드 미일치 공고는 보류하지 않고 유지(`require_keywords`를 UI가 보내지 않음), 클라우드 작업자의 300초 제한·SMTP 실패 재시도 없음, 로컬 index.html의 알림 링크가 공개 주소를 가리킴.
- 검증: `python -m unittest discover -s tests` 182개 OK(4 skip). Ruff는 .venv에 없어 실행 못 함. 실제 메일 발송·배포 없음.
- 이력서(비공개 resum_summary `bd08468`): '오류 0건이어도 남는 실제 오류 가능성(최대 약 26%)'을 정밀도(정상으로 확정한 건 중 실제 정상 비율)의 95% 하한으로 바꿈(10건 모두 맞혀도 약 74%). 경력기술서·포트폴리오 7장 재생성, 쪽수 3·10·22 유지, 로컬 제출본·합본(32쪽) 교체.
- 같은 날 후속(사용자 요청, 공개 배포 보류): 저장 알림 "데이터·AI 전반 (테스트)"로 `collect`만 실행(메일 미발송, alerts.json 해시 불변). 검색 579 → 후보 355, 원문 확인 100건(상한) 중 메일 대상 26건(상한 30), 원문 미확인 255건. 제외: 검색 단계 마감 71·원문 마감 21·이미 보냄 43·지역 26·목록 71·상태 미확인 22·요건 보류 22(지원 버튼 미확인 14, 경력 미확인 8)·요건 탈락 9(직무 불일치). 26건 모두 마감일이 오늘 이후이거나 '채용 시 마감'. 플랫폼은 사람인 20·인크루트 6이고 잡코리아·캐치·원티드는 0건. 증빙 ignored `result/search_quality/alert-count-20261020/collect.json`.

## 2026-10-20 밤: 독립 검토 반영 — 공고 검색 누락 수정과 서버 구독 본인 전용 정리 (Claude)

- 원인(독립 검토): '활성 지원 버튼 필수' 규칙 때문에 잡코리아·원티드가 구조적으로 0건이었고, 상세 확인 예산 100건이 그런 공고와 비공고 URL에 쓰였다. 직무 패턴도 `\bAI\b`가 'AI엔지니어'를 못 잡는 등 좁았다.
- 사용자 결정 반영: ① 마감일(또는 상시·원티드 접수 중) 근거가 있고 비활성 버튼 근거가 없으면 버튼을 못 읽어도 메일에 넣고 "지원 버튼 미확인" 표시, ② 경력은 요청 범위와 겹치면 포함, ③ 헤드리스 렌더러 미사용(초안 `public_browser.py`·`public_snapshot.js`·`render.js`·`package.json` 삭제, `1b0e888`에 남음), ④ 서버 구독은 무료 플랜·본인 전용, ⑤ 공개 빌드에서 구독 기본 제외.
- 검색 품질: 지원 버튼 문구 하나로 공통화(`postings.APPLY_LABEL`, 바로지원·인크루트 지원·즉시 지원), 추천 영역 버튼 제외, 원티드 `__NEXT_DATA__`(접수 상태·마감·경력·근무지), 잡코리아·인크루트 검색 카드의 근무지·경력·버튼(`requirements_card`), 같은 공고로 가는 리다이렉트를 실제로 따라감, "A OR B"를 사이트 검색창에 나눠 넣음, 원문 카드 상한 60→100. 직무군 확대(AI·ML 영문 약어 경계, 데이터 엔지니어, Product Analyst, 그로스, BI, Research Scientist, 통계 분석)와 제목 제외(강사·교육생·국비·부트캠프·방사선사·라벨링·데이터 수집 직원, 분석 업무 없는 영업). 경력: 쉼표별 해석, 경력무관 항상 통과, `4년~10년`·`3+ years`·`Junior`·`3년차 이상`·`3년 이상 7년 이하` 인식.
- 상세 확인 예산: 확인 불가 URL은 예산 전 제외, 직무명이 맞는 후보 먼저, 플랫폼 교대로 최대 160건. 후보별 결과를 `result/job_alerts/runs/<알림ID>.json`(ignored)에 저장. 메일·화면·상태 문구에 보류·상세 미확인·지원 버튼 미확인 건수 표시. UI·README·docs 문구를 실제 동작에 맞춤(키워드는 거르지 않고 우선순위만).
- 실측(저장 알림, 메일 미발송, alerts.json 해시 불변, Tavily 15회): 이전 선정 26(사람인 20·인크루트 6, 잡코리아·캐치·원티드 0, 상세 미확인 255) → **선정 30(상한) = 잡코리아 12·사람인 10·인크루트 5·원티드 3, 캐치 0**. 상세 확인 72건 만에 상한 도달(마감 28·상태 미확인 9(모두 캐치)·경력 근거 없음 4), 확인 불가 URL 15건 사전 제외. 증빙 ignored `result/search_quality/alert-count-20261020-after/`.
- 독립 표본 재대조(무료 원문 검색만·상한 해제·메일 없음): 사람인·잡코리아·인크루트 포함 판정 21건 중 18건 통과, 2건은 이미 보낸 공고, 1건(인크루트)은 사이트 검색 결과에 없음. 이전에는 22건 중 6건만 메일 반영. 3개 플랫폼 상한 해제 시 상세 461건 확인·279건 통과(직무 불일치 72·제외 18·경력 불일치 31).
- 서버 구독(본인 전용): `ALERT_ALLOWED_EMAILS` 허용 주소만 코드 요청·확인·로그인(다른 주소는 같은 응답으로 조용히 무시), 코드 요청 `create_user:false`, 코드 확인 횟수 제한(주소·IP·전체), 비밀값 용도별 분리(worker·수신 해지(`v1.` 버전·이전 키 병행)·횟수 제한 pepper), DB `alert_health()`로 준비 판정, 발송 기록 생성 14일 후 상태 무관 삭제, SMTP는 넘기기 전 오류만 재시도·Resend `sending` 재개 시 마감 재확인으로 취소하지 않음, worker는 검증된 조건만 사용, worker 호출 POST. SQL은 재실행 가능하게(정책 drop 후 생성, cron unschedule 후 schedule), `alert_save`에 Vault 허용 주소·동의 버전·크기 검사. 공개 빌드는 `--with-subscriptions`일 때만 구독 화면·API·런타임 포함, 로컬 UI의 운영 구독 링크(404) 제거. AGENTS.md에 두 단계 경계 추가, 설정 할 일은 `docs/server_alerts.md`.
- 검증: `uv run python -m unittest discover -s tests` 209개 OK(4 skip, 이전 182개), 신규 `tests/test_cloud_alerts.py` 12개, `uvx ruff check --select E9,F`(변경 파일) 통과, `git diff --check` 통과. 실제 메일·Supabase 원격·Vercel 배포는 하지 않음(공개 배포 보류). SQL은 실제 Postgres에서 실행하지 못함(psql·docker 없음).

## 2026-10-21 새벽: 조건 통과 공고 전체를 구글 시트로, 메일은 30건 상한 유지 + Codex 지적 반영 (Claude)

- 사용자 요청: 배포 구조는 그대로 두고, 지금은 조건에 맞는 공고 전체를 구글 시트에 저장하고 메일은 30건 상한으로만 보낸다. 로컬 알림은 상세 확인 예산 없이 후보를 전부 확인하고(메일 상한에서 멈추지 않음), 조건 통과 전체를 시트로, 메일은 앞에서부터 상한만큼 보낸다. 못 보낸 공고는 발송 기록에 안 남아 다음 메일로 이어진다. 화면 검색·서버 worker는 시간 제한 때문에 기존처럼 상한에서 멈춘다(worker 상세 확인 160건).
- 시트 연결: `alerts/sheet.py`(본인 Apps Script 웹 앱 주소 `ALERT_SHEET_URL` + 토큰 `ALERT_SHEET_TOKEN`, Apps Script 결과 리다이렉트만 따라감), `deploy/sheets/job_alerts.gs`(URL 기준 추가/갱신, 첫 메일 발송일 유지, 수식 주입 방지). 시트 실패는 메일을 막지 않고 상태에 남김. 미리보기는 시트에 쓰지 않음. 발송 URL 기억 1000→5000, 실행 잠금 만료 15분→60분. 메일 꼬리말에 "조건 통과 N건 중 M건" 안내.
- Codex 지적 반영: ① `경력(3년 이상)`·`경력 : 경력(2년 이상)` 같은 괄호형 경력을 근거 추출 단계에서 인식하고, 자격요건 구역에 연차가 없으면 다음 근거로 넘어감. 공고 자신의 JSON-LD 설명을 본문보다 먼저 사용. ④ 캐치 상세의 '방금 본 공고와 비슷한 공고'·'다른 회원이 함께 본 공고' 영역을 잘라내고, 그 아래 버튼은 지원 근거로 쓰지 않음. ②(iframe 본문·상시채용 문구)는 사용자 정책상 상시는 포함하되 "채용 시 마감(원문 확인)"으로 표시하는 현재 동작을 유지, iframe 통합은 미구현. ③(캐치 목록 원문 어댑터)은 목록이 JavaScript 전용이라 렌더러 없이 불가해 미구현.
- 확인한 사실: 캐치가 이 PC를 일시 접속 제한(Cloudflare 1015, 상태 200 차단 페이지)해 오늘 캐치 상세 '확인 불가'의 원인이었다. 429·차단 페이지를 `rate_limited`로 판정하고 같은 회차에는 그 사이트를 더 요청하지 않도록 했다. 접속 제한이 걸린 상태라 실시간 collect 재실행은 하지 않았다.
- 정리: 사용자 요청으로 저장해 둔 요청문 md(Codex 요청 프롬프트 2개, Claude 검토 요청문 1개)를 삭제. 검수·검토 결과 보고서는 유지.
- 검증: `uv run python -m unittest discover -s tests` 217개 OK(4 skip), `uvx ruff check --select E9,F` 변경 파일 통과. 실제 시트·메일·원격 작업은 하지 않음.

## 2026-10-21: 플랫폼 이력서 저장 자동화와 공통 이력서 최신화 (Claude)

- 사용자 요청("에이전트 시켜놓고 내가 버튼 눌러야 하는 건 트렌드가 안 맞다, 나중에 보고 수정")으로 사이트 저장을 자동화: `ResumeSync.auto`가 로그인 대기(사람이 로그인·2차 인증) → 편집 화면 이동 → 기존 성공 연결 또는 단일 항목명 일치 연결 → 기존 값 백업 → 입력 → 입력칸 바로 뒤 저장 버튼(원티드는 자동저장) → 새로고침 후 다시 읽어 확인. 다시 읽은 값이 다르거나 연결·저장 버튼이 불명확하면 재시도 없이 '확인 필요'. 사이트별 결과 `result/site_sync/auto-<site>.json`, 요약 `auto-report.md`(바꾼 항목·연결 못 한 항목·못 한 것·백업 위치). 반복 행 생성·첨부·공개 설정·동의 체크·지원서 제출은 하지 않음. UI는 동의 한 번 후 사이트별로 로그인될 때까지 4초 간격 재시도(최대 20분), 기존 '직접 검수' 방식은 남김. AGENTS·README·화면 안내·process 문구 갱신.
- 공통 이력서 `result/resume_profile/profile.json`(ignored)을 최신 제출 이력서(resum_summary `f65bf73` 이력서.md)로 다시 만듦: 제목·소개·경력(주요 프로젝트 5건)·직무·학력(고교 포함)·개인 프로젝트+석사 과제·수상·경진대회·자격·기술·활동·링크, 항목마다 원문 문단 근거. 자기소개서는 새 이력서에 없어 비움(이전 초안은 `profile.backup_20261021.json`). 연락처는 계정에 이미 있어 비움.
- 검증: 신규 `AutoSyncTests` 3개(자동 저장·확인·보고서, 로그인 대기, readback 실패 시 확인 필요), 화면 흐름 테스트 갱신, 전체 220개 OK(4 skip). 실제 5개 사이트 저장은 사용자 확인 후 진행.

## 2026-10-20 밤: 제출 문서 지적 반영·경험 추가·개인 프로젝트 포트폴리오 (Claude)

- 비공개 resum_summary(`ec3c398`, `f65bf73`, `9681ef2`, `481dac1`): Codex 교차 검수 나머지 지적 반영(배포 원문 범위, 운영·구현 구분, 수상·자격 정식 명칭, 일하는 방식 범위, 기준값 산출 한 문장, 쪽 넘김). '실제 오류 가능성'은 정밀도(정상으로 확정한 건 중 실제 정상 비율) 하한으로 표현.
- 사용자 결정으로 경험 추가: 개인 프로젝트 4건(job_agent·Quant_Trading·AI_agent·advertisement_apple), 연구·산학 과제의 판단 과정, 대구 빅데이터 경진대회 본선·빅콘테스트·K-Circle·KSRS·한국사·패스트캠퍼스, 동아리 기간. 연구소 조교·SQL 교육은 제외. Quant_Trading 포스터는 발표 전이라 쓰지 않음. 이력서 4쪽, 경력기술서 12쪽, 합본 34쪽.
- 개인 프로젝트 포트폴리오 8장을 경력 포트폴리오와 별도 파일로(`portfolio/personal_projects/`, 학회 내용 없음). 석사 연구는 이전 `포트폴리오.pdf` 사용.
- 노션 포트폴리오 페이지: AI_agent 주소를 GitHub로, '개인 프로젝트' 표 추가. 로컬 `공통 이력서 정리/` 제출본 교체. 개인 Google Drive 사본은 아직 이전 버전.

## 2026-10-21: 5개 플랫폼 이력서 실제 최신화 (Claude in Chrome)

- 자동 전용 창(Playwright)으로 실행했더니 Google 로그인이 "안전하지 않은 브라우저"로 거부돼(자동화 플래그·--no-sandbox) 중단. 사이트 자체 아이디 로그인은 가능하지만, 서비스로 확장하려면 사용자 Chrome 안에서 동작하는 확장 프로그램 방식이 맞다는 점을 확인.
- 사용자 지시로 사용자 Chrome(구직 계정 프로필)에서 원티드·캐치·인크루트·사람인·잡코리아의 제목·소개·경력·학력 칸을 최신 이력서로 바꾸고, 저장 후 새로 불러와 확인. 사진(캐치·인크루트·잡코리아), 병역(사람인·잡코리아, 지원서 근거와 사용자 확인), 사람인 경력기술서·경험/활동 4건, 인크루트 자기소개서(새 이력서 사실만으로 작성) 후 작성 완료. 이전 경력 글의 내부 제품명은 모두 제거됨.
- 잡코리아·인크루트(EUC-KR)는 긴 줄표가 '?'로 깨져 ':'로 바꿔 재저장. 사이트별 수정 전 값·결과는 ignored result/site_sync/chrome-2026-10-21/.
- 사용자 요청으로 사람인 자격/어학/수상 8건(자격증 4·어학 1·수상 3)도 추가하고 새로 불러와 확인.
- 사용자 요청("다 추가하라고")으로 캐치에 학사 학력·자격증 4·어학 1·수상 3·교육 1·병역을 추가하고 미완성 저장 후 새로 불러와 값 확인. 인크루트에는 학사 학력·병역(해병/병장)·자격증 4·수상 3을 섹션별 저장으로 넣고 새로 불러와 확인(어학은 시험 '일'이 자료에 없어 제외, 고등학교도 근거 없어 비움). 캐치 병역 군별은 '해군'을 '해병'으로 바로잡아 재저장.
- 남은 것: 원티드 스킬·수상·링크 행, 캐치 고등학교, 인크루트 어학·주요활동. 자동 저장 코드(ResumeSync.auto)는 EUC-KR 사이트용 문자 치환이 아직 없음.

## 2026-10-24: 플랫폼 이력서 전체 변환(소개·자소서·경력·석사 연구·개인 프로젝트) — 캐치·인크루트·원티드 완료, 사람인·잡코리아 로그인 대기 (Claude in Chrome)

- 원본: 비공개 resum_summary `0fefe30`의 `resume/platform_profile.md`(한 줄 소개·짧은/긴 자기소개·경력 설명·프로젝트 5건·석사 연구 4건·개인 프로젝트 4건)와 `이력서.md`(`68fc214`, 학력·수상·자격·활동). 공통 이력서 `result/resume_profile/profile.json`(ignored)을 이 둘에서 다시 만들고(`profile.backup_20261024.json` 백업) 사이트별 글자 수에 맞춰 문장 단위로 넣음(중간에서 자르지 않음, 줄인 글 없음). 내부 제품명·알고리즘 실명·함수명·운영 건수는 원본 단계에서 이미 제외됨.
- 캐치: 제목, 담당업무 및 성과(소개+프로젝트 5건), 경력기술(자기소개 4단+결론, 석사 연구 4건, 개인 프로젝트 4건), 활동(Gol:D 동아리 2022.03~2024.07), 포트폴리오 URL(GitHub) 저장 후 새로 불러와 확인. 고등학교는 캐치가 전공계열(문과·이과·실업)을 필수로 요구하는데 자료에 없어 비움.
- 인크루트: 제목, 경력 업무(소개+프로젝트 5건), 대학원 '수업 및 프로젝트'(석사 연구 4건), 주요활동(Gol:D, 개인 프로젝트 4건), 교육수료(패스트캠퍼스), 자기소개서(제목=긴 한 줄 소개, 본문=긴 자기소개 1,178자) 저장·확인. 어학(TOEIC Speaking)은 취득일 '일'이 필수인데 자료에 없어 미입력(입력 시 브라우저 경고창).
- 원티드: 간단 소개(짧은 자기소개 234자), 경력 성과 제목·설명(소개+프로젝트 5건), 대학원 이수·연구 내용(석사 연구 4건), 학사·고등학교 학력 추가, 기타 항목 2건(Gol:D 동아리, 개인 프로젝트 4건) 추가 후 새로 불러와 확인. 어학시험 행은 날짜 '일'이 필수라 미입력(TOEIC Speaking은 기타 항목에 이미 있음). 상세 칸은 입력 후 포커스를 옮겨야(Tab) 자동저장됨.
- 사람인·잡코리아: 이 Chrome에서 로그아웃 상태(로그인 페이지)라 미진행. 로그인은 사용자만, 비밀번호는 입력·보관하지 않음. 로그인 후 같은 방식으로 진행 예정.
- 교훈: 한글 문장을 도구 인자에 유니코드 이스케이프로 쓰면 글자가 틀어짐 → 원문 한글 그대로 입력. 인크루트 '모두 저장'은 변경이 없거나 필수값이 비면 경고창으로 탭이 멈추므로 멈추면 탭을 닫고 새 탭에서 확인.

## 2026-10-24: 포트폴리오·경력기술서 PDF 첨부 (Claude in Chrome)

- 첨부 파일: `공통 이력서 정리/윤태준_포트폴리오_데이터사이언티스트.pdf`(29장 합본 포트폴리오), `윤태준_경력기술서_데이터사이언티스트.pdf`. 이전 포트폴리오 파일(_이전본_20261024)은 올리지 않음.
- 캐치: 포트폴리오 칸(파일 1개)에 합본 포트폴리오 PDF 첨부, GitHub URL은 유지, 새로 불러와 확인. 이전 첨부 없음.
- 인크루트: '포트폴리오 및 첨부서류'에 포트폴리오(합본)·경력기술서 2건 첨부, 새 탭에서 이력서 보기로 확인. 이전 첨부 없음(삭제한 것 없음). 경력이력서 PDF는 별도 이력서 칸이 이력서 본문과 중복이라 올리지 않음.
- 원티드: 이력서에 파일 첨부 칸이 없고(목록의 '파일 업로드'는 PDF를 새 이력서로 변환·생성하는 기능) 링크(GitHub)만 있어 업로드하지 않음.
- 사람인·잡코리아: 로그아웃 상태라 미진행(로그인 후 첨부 예정).

## 2026-10-24(이어서): 사람인·잡코리아 텍스트·첨부 반영 (Claude in Chrome)

- 사람인(구직 전용 프로필 크롬): 제목, 경력 담당업무(소개+프로젝트 5건), 경력기술서(자소서 4단+석사 연구 4건+개인 프로젝트 4건), 대학원 논문/작품(논문+산학 과제 요약), 자기소개서(새로 추가: 제목=긴 한 줄 소개, 본문 1,178자), 포트폴리오/기타문서(포트폴리오 PDF·경력기술서 PDF) 저장 후 새로 불러와 확인. 고등학교·학사는 이미 있었음. AI 커리어 소개·AI 스킬 제안 팝업은 적용하지 않고 닫음.
- 잡코리아(다른 크롬, 로그인 상태): 경력 주요 성과(소개+프로젝트 5건), 자기소개서(제목+본문에 석사 연구·개인 프로젝트 포함), 제목, 포트폴리오 PDF·경력기술서 PDF 첨부 후 저장·확인. 주의: 편집 화면(Write?rNo=27731622)에서 저장하면 새 이력서 번호(31679004)로 저장돼 이력서 목록에 3건(기존 기본이력서 10.21 / 새 제목 이력서 10.24 / 제목 없는 '이력서' 10.24 — 중단된 자동 임시저장이 만든 빈 이력서)이 생김. 삭제·기본이력서 변경은 하지 않고 사용자 판단으로 남김. 이전 첨부 '포트폴리오.pdf'는 삭제하지 않음.
- 로그인: 사용자가 구글 계정 프로필 크롬(Browser 1)에서 사람인을 로그인, 잡코리아는 다른 크롬에서만 로그인되어 있어 두 브라우저를 오가며 진행(비밀번호는 입력·보관하지 않음).
- 못 한 것: 어학시험 날짜 '일' 없는 곳(인크루트·원티드), 캐치 고등학교 전공계열, 원티드 첨부 칸 없음, 사람인 경험/활동에 개인 프로젝트 별도 항목 추가 안 함(경력기술서·자기소개서에 포함).

## 2026-10-25: 개정 PDF 재첨부(캐치·인크루트·사람인) + 카카오게임즈 지원서 작성(미제출) (Claude in Chrome)

- 개정 PDF(같은 파일명, 포트폴리오 35장 3.64MB·경력기술서 383KB)로 기존 첨부를 교체: 캐치(포트폴리오 칸 교체, 새로 불러와 확인), 인크루트(포트폴리오·경력기술서 삭제 후 재첨부, 새 탭에서 확인), 사람인(포트폴리오/기타문서 2건 교체, 확인). 텍스트 칸은 platform_profile.md가 바뀌지 않아 추가 수정 없음.
- 잡코리아는 개정 PDF 교체 미완료: 이 크롬에서는 로그아웃 상태(로그인된 다른 크롬 필요). 이력서 3건은 삭제·기본이력서 변경 없이 유지, 교체는 새 내용 이력서(rNo=31679004)에만 할 예정.
- 카카오게임즈 데이터인사이트팀 분석가(마감 2026.10.25 23:59) 지원서를 사용자 요청으로 입력만 하고 제출하지 않음(탭 유지). 입력: 기본정보·학력(고등/학사/석사)·경력(위즈코리아)·어학(TOEIC Speaking IM3, 취득일 '일'은 자료에 없어 1일로 임시)·자격 4건(취득일 '일'도 1일 임시)·제출서류 2건·자기소개서 2문항(초안). 비워둠: 병과, 지원경로, 추천인, 개인정보 동의, 고등학교 계열.
- 교훈: Greeting ATS 폼은 자동완성 목록이 늦게 뜨고 선택 직후 레이아웃이 밀려 첫 클릭이 무시되기 쉬움. 날짜 팝업은 상단 입력칸에 직접 입력 후 Enter, 팝업이 안 닫히면 빈 곳 클릭.

## 2026-10-25(이어서): 잡코리아 개정 PDF 첨부

- 사용자 로그인 후 새 내용 이력서(rNo=31679004)에는 개정 PDF가 없고(옛 포트폴리오.pdf·증빙자료만) 포트폴리오·경력기술서 개정본 2건을 추가해 저장. 잡코리아는 저장할 때마다 새 이력서 번호를 만들어 rNo=31686089(10.25)가 생겼고, 이 이력서에 새 내용+개정 PDF 2건이 모두 있음(옛 포트폴리오.pdf·증빙자료.pdf도 그대로). 삭제·기본이력서 변경 없음.
- 현재 이력서 4건: 기본이력서(10.21, 옛 기본), 제목 있는 31679004(10.24, 개정 PDF 없음), 제목 없는 31686089(10.25, 새 내용+개정 PDF), 빈 '이력서'(10.24). 31686089는 제목이 비어 있어 사용자 확인 필요. 더 저장하면 또 복제되므로 수정은 마지막 한 번만.
- 잡코리아 rNo=31686089에 제목을 다시 넣고 저장해 목록·보기에서 확인. 목록의 '수정' 링크(Resume/Edit?RNo=)로 저장하면 같은 번호에 덮어써 복제가 생기지 않음(Write?rNo= 경로는 저장 때마다 새 번호 생성). 이력서 4건 그대로, 개정 PDF 2건 유지. 사용자가 직접 할 일: 31686089를 대표로 지정, 나머지 3건(기본이력서 10.21, 제목 같은 10.24, 빈 '이력서' 10.24) 삭제.

## 2026-10-26: 경력·경험기술서 합본, 포트폴리오 링크, 노션 포트폴리오 갱신

- resum_summary `e7f6448`: 경험기술서(석사 연구·산학·학부 프로젝트·경진대회 8건, 개조식)를 경력기술서와 합본한 `윤태준_경력·경험기술서_데이터사이언티스트.pdf`(21쪽) 생성, 포트폴리오 학위논문 장에 github.com/tabjun/anomaly_detection 링크 추가. 새 PDF는 `공통 이력서 정리/`에 반영, 이전본은 `이전본_20261026/`.
- 노션 포트폴리오: 상단에 경력 섹션과 '💼 경력 프로젝트' 갤러리(5장, 제품명·코드명 일반화) 추가, 프로젝트 수행 갤러리에 개인 프로젝트 4장 추가, 연구 카드의 학위논문 코드 링크를 anomaly_detection으로 교체.
- 채용 플랫폼(캐치·인크루트·사람인·잡코리아) 첨부는 아직 10-25 21:51판(개조식·링크 반영 전) — 교체 필요.
- 플랫폼 첨부 최신본 교체(10-26, 구직 전용 프로필 크롬): 캐치(포트폴리오 교체, 고등학교 이과계열·성별 입력으로 미완성 해제), 인크루트(포트폴리오·경력기술서 교체, 모두 저장), 사람인(포트폴리오·경력기술서 371KB 교체, 섹션 저장, AI 소개 미적용), 잡코리아 rNo=31686089(Edit 경로로 같은 번호에 저장). 옛 '포트폴리오.pdf'·증빙자료는 유지.
- 경력기술서·경력·경험기술서·경력이력서 머리글 연락처 줄에 Notion 포트폴리오 링크 추가(resum_summary 2ff7acb 이후). 노션 링크판 경력기술서로 인크루트(이전 행 삭제·내 파일함 최신본 첨부 확인)·잡코리아(구분 '기타', 첨부파일 관리에서 371.97K 확인)·사람인(372KB)·캐치(이력서 포트폴리오 칸에 경력기술서 추가, 첨부파일관리 372KB) 재교체. 인크루트 삭제 확인창(native confirm)이 탭을 멈춰 탭을 새로 열어 진행.
- 캐치 첨부 초기화(10-26): 첨부파일관리의 기존 파일(포트폴리오 2건·경력기술서)을 모두 삭제한 뒤 이력서 포트폴리오 칸에 포트폴리오(3.5MB)·노션 링크판 경력기술서(372.0KB)를 새로 첨부하고 '이력서 저장'(완성도 80%). 첨부파일관리에 두 파일과 GitHub URL만 남은 것을 확인. 팝업에서 두 번째 파일은 보이는 file 입력이 아니라 숨은 fileinput에 올려야 목록에 추가됨.

## 2026-10-26: 미래에셋증권 자소서 4문항, 저축은행 마이데이터 지원 Word 3종

- 미래에셋증권 AI/Tech (Security) Specialist 자기소개서 4문항(각 100~2000자: 경력기술서·입사지원동기·성격/능력/장단점·가장 오래 지속한 업무 경험) 작성. 기존 자소서 전체를 정리해 빅콘테스트(1,350만 건, AUC 0.75)·생검 재현율 교훈·송아지 현장 적용을 보강하고, 서류 간 불일치(동아리 인원, 기준값 산식)는 쓰지 않음. 4번은 이상 탐지 건 사전 분류 모델을 문제정의-가설-실험설계-검증-결과로 서술. 지원서 화면 입력은 별도 세션에서 진행(제출은 하지 않음).
- 인크루트 커리어커넥트 '대형저축은행 마이데이터사업팀원(데이터분석가)' 공고용 경력이력서(4쪽)·경력기술서(14쪽)·자기소개서(2쪽) Word를 `etc/취업/지원_커리어커넥트_저축은행마이데이터/`에 생성. 이력서 역할명·한 줄 소개만 데이터 분석가로 바꾸고 본문은 공통 원본 재사용.
- 미래에셋증권 지원서 화면 입력(10-26, 구직 전용 크롬 프로필, 제출 안 함): 자기소개서 4문항을 보강 최종본(1653/1609/1946/1527자)으로 저장, 병역(해병·병장·보병·2018.09.17~2020.05.02·만기제대), 고교(대구가톨릭대학사대부속무학고 2014.03~2017.02), 대학(계명대 통계학 학사 3.45/4.5, 석사 96.75/100·세부전공·논문 제목, 지도교수는 사용자 직접 입력), 수상 2건(학회 장려상 2023.11.03·2023.05.12, K-Circle은 사용자가 삭제), 교육(SQL 활용 22시간, 2024.10~11) 저장. 자격 4종은 등록번호가 필수라 미입력, 패스트캠퍼스 교육은 시작 연월 필수라 미입력, IT활용능력 미입력. 사용자 확인 필요: 성명(한글) 'taejun yoon', 직전연봉 36,000만원(3,600 오타 의심), 주소 공란. 사이트는 '화면에서 직접 수정' 모드에서 섹션별 저장, 학교·전공·자격증명은 검색 팝업으로만 입력.
- 미래에셋 후속(10-26): 자소서 4문항을 1990~1999자로 재작성(1992/1996/1999/1992). 성격 문항은 기존 자소서(제약·자동차·기타·AI역검)의 '경험은 넓게, 집중은 깊게', 유도대회 '인정' 서사로 성격과 행동 이유가 드러나게 다시 씀. 자격 4건(사회조사분석사 2급·ADsP·SAS Base·한국사 3급)의 번호를 증빙 PDF에서 확인해, IT활용능력(사용자 지정 수준·기간)과 함께 지원서 입력 세션에 전달. 화면 입력은 그 세션이 담당하고, 제출은 하지 않음.
- 미래에셋 지원서 추가 입력(10-26): 자격 4건(ADsP, 사회조사분석사 2급, SAS Certified Specialist: Base Programming Using SAS 9.4, 한국사능력검정 3급, 증빙 파일의 취득일·등록번호·발행기관 기준) 저장, IT활용능력 5건(OA 파워포인트·워드 중급 3년, Python 중급 5년, R·SAS 초급 2년, 사용자 지시값) 저장. 자격증 검색 팝업의 '직접입력'은 iframe 안 alert로 탭이 멈추므로 모든 프레임의 alert/confirm을 덮어쓴 뒤 눌러야 함. 패스트캠퍼스 교육은 시작 연월이 없어 아직 미입력.
- 미래에셋 자기소개서 4문항을 원래 세션의 최종본(1992/1996/1999/1992자)으로 다시 저장하고, 새로고침한 화면의 저장값으로 글자 수와 첫·끝 문장을 확인. 사이트가 소제목의 '—'를 '―'로 바꿔 저장함. 제출은 하지 않음.
- 미래에셋 교육이력 정정: 사용자 지시로 SQL 활용(인천e배움캠퍼스) 행 삭제, 패스트캠퍼스(머신러닝과 데이터분석 A-Z, 2022.07~08, 93시간)·인프런 2건(테디노트 파이썬 3시간, Pandas 기초 1시간, 2022.03) 저장. 교육 칸은 과정명·기관·주요내용이 20자 제한이라 줄여 씀. 자기소개서 4문항은 최종본(1992/1996/1999/1992자)으로 저장된 상태 유지.
- 미래에셋 자기소개서 1~3번을 사용자 재수정본(지원동기 전면 재작성, 빅콘테스트 삭제, 성격 문항의 능력 사례를 심박 연구로 교체)으로 다시 저장. 새로고침한 조회 화면에서 4문항 1994/1994/1994/1992자와 '빅콘테스트' 미포함을 확인. 제출은 하지 않음.
- 미래에셋 자기소개서 1·2·4번을 사용자 재수정본(지원동기를 통계학 계기로 시작, '회귀 테스트 N개' 같은 표현 삭제)으로 다시 저장. 새로고침 후 조회 화면의 4문항(1998/1997/1994/1994자)이 원본 파일과 SHA-256까지 일치('―'→'—' 표기만 정규화)하고 '회귀 테스트'·'빅콘테스트' 미포함을 확인. 제출은 하지 않음.
- 미래에셋 자기소개서 2번(입사지원동기)에서 '미래에셋 3.0의 방향' 문장을 AI 활용·통계 검증 방식 문장으로 바꾼 재수정본(1996자) 저장. 새로고침 후 4문항이 원본 파일과 해시까지 일치하고 '미래에셋 3.0' 표현이 없음을 확인(1번의 날짜 2023.03 등만 남음). 제출은 하지 않음.

## 2026-10-26: 원티드 이력서 개편, 에이블리 데이터 분석가 지원 서류

- 원티드 기본 이력서 수정 내용(저장 후 새로고침으로 확인):
  - 간단 소개: 문제 정의·검증으로 해답을 도출하는 데이터 사이언티스트 관점으로 다시 씀
  - 링크: Notion 포트폴리오 추가
  - AI 활용 경험: 3개 항목(최대 3개, 항목당 50자)으로 구체화
  - 경력: 주요 성과 5개를 프로젝트별 개조식으로 정리(분석환경 및 활용기술 포함). 기간 달력은 연도 선택 시 닫혀 입력되지 않아 제목에 기간을 붙임
  - 파일 업로드: 개인정보 수집·이용 동의(선택) 창이 떠 동의하지 않고 닫음. 업로드는 사용자가 직접 하기로 함
  - JS로 값을 직접 넣으면 저장되지 않으므로 form_input만 사용
- 에이블리 지원 서류: `etc/취업/에이블리/`에 이력서(4쪽), 경력·경험기술서(17쪽), 포트폴리오(29쪽)를 Word·PDF로 생성
  - 공통 원본은 그대로 두고 소개·역량·프로젝트 문장만 분석가 관점으로 덮어씀
  - 기술서 소제목은 '문제 정의 → 가설과 실험 → 결과와 액션 아이템' 흐름에 맞추고, 제품·서빙 구현 단계와 테스트 개수 표현은 뺌
  - 포트폴리오는 기존 35장에서 분석 중심 29장을 고르고 쪽번호를 새로 매김
- 미래에셋 지원동기는 회사 소개 문단과 '미래에셋 3.0' 문장을 빼고 저장(제출 안 함).
- 노션 포트폴리오: '경력 프로젝트' 아래에 지원 서류 표(📎 이력서·기술서·포트폴리오)를 추가. 행은 이력서 / 경력·경험 기술서 / 포트폴리오이고, 행마다 에이블리용 PDF를 '파일' 칸에 올림. 순서 칸(숨김)으로 정렬. 포트폴리오 PDF는 장을 골라 내며 겹쳐 들어간 내부 데이터를 정리해 6.1MB에서 2.6MB로 줄임(29쪽 모두 원본과 화면 비교로 같음 확인).
- 원티드 링크: GitHub 프로필 링크 1개를 프로젝트별 저장소 링크 4개(이상치 탐지 anomaly_detection, job_agent, Quant_Trading, advertisement_apple)로 바꾸고 Notion 포트폴리오는 유지. 저장 후 새로고침으로 확인.
- 포트폴리오 축소(10-26): 공통 합본 포트폴리오에서 API 게이트웨이·위험 기준값 장을 빼고 탭·목차·개요를 함께 정리해 35장에서 33장으로 줄임(resum_summary 커밋). 이전 35장은 `공통 이력서 정리/이전본_20261026_포트폴리오35장/`에 백업. 에이블리용 포트폴리오도 새 원본으로 다시 골라 27장(2.5MB)으로 만들고, 노션 지원 서류 표의 파일을 교체.
- 노션 '포트폴리오 갤러리' 하위 페이지를 새로 만듦: 프로젝트 9개(경력 3, 석사 연구 4, 개인 2)를 카드로 정리. 카드 표지는 포트폴리오 장 이미지이고, 구분·핵심 질문·기간·상태·기술을 표시. 메인 포트폴리오의 경력 섹션 위에 링크를 둠. 공개 페이지에서 표시 확인.
- 플랫폼 포트폴리오 교체(10-26 12:40~12:52): 캐치·인크루트·사람인·잡코리아(rNo=31686089, Edit 경로) 이력서의 포트폴리오 첨부를 `공통 이력서 정리/윤태준_포트폴리오_요약본_데이터사이언티스트.pdf`(27장, 2.4MB, 에이블리용과 같은 축약본)로 바꿈. 이전 35장 첨부는 각 이력서에서 빼고, 경력기술서(14쪽 노션 링크판)는 그대로 둠. 작업한 Chrome 프로필의 Google 계정은 구직용이고, 사람인·잡코리아 이력서의 이메일도 구직용 주소임을 확인. 각 사이트에서 저장 후 다시 열어 첨부 목록을 확인했고, 제출은 하지 않음. 잡코리아의 옛 '포트폴리오.pdf'와 자격증 증빙은 그대로 둠.
- 핵심 포트폴리오 15장(10-26 15:02): `공통 이력서 정리/윤태준_포트폴리오_핵심_데이터사이언티스트.pdf/.pptx`. 구성은 표지·자기 소개, 경력 분석 2건(사전 분류 3장, 행위 이상 탐지 2장), 일하는 방식, 석사 연구 3건(심박·학위논문 3장, 송아지 2장, 생검 2장). 개인 프로젝트·보안 자동화·목차·파트 표지는 빼고, 자기 소개와 일하는 방식의 예시를 남은 프로젝트 기준으로 바꿈(resum_summary build_pptx6.py). 플랫폼 첨부는 아직 27장 요약본.
- 핵심 포트폴리오 Google Slides 업로드(10-26 17:03): 개인 Google Drive에 새 폴더 `윤태준 핵심 포트폴리오 (2026-10-26)`를 만들고 15장 PPTX·PDF 원본을 올린 뒤, PPTX를 'Google Slides로 저장'으로 변환(Slides 15장). 격자 보기로 15장이 모두 들어오고 글자·그림이 깨지지 않은 것을 확인. 업로드는 Chrome에서 Drive 업로드 입력란에 파일을 직접 넣는 방식(연결 도구로 큰 파일을 보내지 않음). 10-19 폴더의 옛 사본은 그대로 둠.
- 핵심 포트폴리오 생검 장 보강(10-26 17:30): 사용자 지적(15장본에서 생검 '통합 모델' 장이 빠져 연구 내용이 반만 남음)으로 14번 장을 '생검 판단 / 개별·통합 모델'로 바꿈. 왼쪽 개별 모델(의사 3명) 도식, 오른쪽 통합 모델 도식, 아래 연구 목적·통합 학습 방식·변수 선택과 결측 보완 3줄. 15장 유지, 다른 장은 PDF 글자 비교로 그대로임을 확인. 생성기는 resum_summary `9551a19`(make_pptx6.py에서 생성). 로컬 `공통 이력서 정리/`의 PDF·PPTX 교체(이전본 `이전본_20261026_핵심15장_생검수정전/`), Drive 폴더의 PDF·PPTX는 같은 링크의 새 버전으로, Google Slides는 같은 파일에서 14번 장만 가져오기로 바꾸고 옛 장 삭제. 플랫폼 첨부는 여전히 27장 요약본.
