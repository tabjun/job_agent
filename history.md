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
