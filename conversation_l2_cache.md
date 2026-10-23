## 플랫폼 이력서 전체 변환 (2026-10-24, 최신, Claude)

- 사용자 요청: 5개 사이트에 경력뿐 아니라 자소서(문제를 정의하고 해결하는 데이터 사이언티스트)·석사 연구·개인 프로젝트까지 모두 담기. 원본 resum_summary `resume/platform_profile.md`(0fefe30)+`이력서.md`(68fc214). profile.json 재생성(백업 `profile.backup_20261024.json`).
- 완료: 캐치(고등학교는 전공계열 필수라 비움), 인크루트(어학은 '일' 없어 비움), 원티드(어학시험 행은 '일' 없어 비움). 미완: 사람인·잡코리아는 이 Chrome에서 로그아웃 → 사용자가 로그인하면 이어서 진행(자소서·경력기술서·경험/활동·학력 고교·사진 유지).
- 첨부(2026-10-24): 캐치(포트폴리오 PDF 1개)·인크루트(포트폴리오+경력기술서) 완료, 원티드는 첨부 칸 없음, 사람인·잡코리아는 로그인 후 진행. 파일은 `공통 이력서 정리/윤태준_*_데이터사이언티스트.pdf`.
- 사람인·잡코리아 반영 완료(2026-10-24): 사람인은 자기소개서 새 항목+첨부 2건, 잡코리아는 새 이력서 번호(31679004)로 저장되어 목록에 이력서 3건(기본이력서 10.21, 새 제목 이력서, 빈 '이력서') — 정리·기본이력서 지정은 사용자 몫. 브라우저 2개(구글 프로필 Browser 1 / 기존 Browser 2)를 select_browser로 전환.
- 주의: 한글 텍스트는 유니코드 이스케이프 말고 원문 그대로 입력. 인크루트 EUC-KR(— 금지), 인크루트 '모두 저장' 경고창 멈춤은 탭 닫고 새 탭. 비밀번호는 입력·보관하지 않는다.

## 5개 플랫폼 이력서 실제 최신화 (2026-10-21, 최신, Claude)

- 사용자 Chrome(구직 계정 프로필, Claude in Chrome)으로 5개 사이트 이력서 갱신·재확인 완료. 결과·백업은 result/site_sync/chrome-2026-10-21/report.md.
- 교훈: Playwright 전용 창은 Google 로그인이 거부됨 → 서비스화는 확장 프로그램 방식 검토. EUC-KR 사이트(잡코리아·인크루트)는 긴 줄표(—) 등 비KS 문자를 바꿔 넣어야 함(ResumeSync.auto에 아직 미반영).
- 병역: 군필·해병·병장·만기제대·2018.09~2020.05(지원서 근거). 인크루트 자기소개서는 새 이력서 사실로 짧게 작성해 넣음(profile.json에는 미반영).
- 사람인 자격/어학/수상 8건 추가 완료.
- 캐치: 학사 학력(계명대 통계학과 2017.03~2023.02), 자격증 4·어학(TOEIC Speaking 130)·수상 3·교육(패스트캠퍼스)·병역(군필/해군→해병 칸 없음, 병장, 만기전역, 2018.09~2020.05) 추가·미완성 저장·새로 불러와 값 확인. 고등학교는 근거 자료에 학교명이 없어 비움.
- 캐치 병역 군별은 처음 '해군'으로 잘못 골라 '해병'으로 고쳐 재저장함(해병 항목이 목록 맨 아래쪽에 있음).
- 인크루트: 학사 학력(2017.03~2023.02)·병역(해병/병장, 2018.09~2020.05)·자격증 4·수상 3을 섹션별 '이 부분만 저장'으로 저장하고 새로 불러와 확인. '모두 저장'은 브라우저 경고창으로 탭이 멈추고 저장되지 않았음(저장 후 탭을 닫고 새 탭으로 확인하는 방식이 안전). 어학(TOEIC Speaking)은 취득일 '일'이 자료에 없어 입력하지 않음.
- 남은 일: 원티드 스킬·수상·링크, 캐치 고등학교·포트폴리오, 인크루트 어학·주요활동·교육수료, 잡코리아 활동 추가.

## 제출 문서 경험 추가·개인 프로젝트 포트폴리오 (2026-10-20 밤, Claude)

- 사용자 선호: 개인 프로젝트·경험은 '무엇을 왜 어떻게 했고 무엇을 고민해 적용했는지'로 쓴다. 학회 내용은 개인 프로젝트 쪽에 넣지 않는다. 정밀도·재현율 같은 지표는 용어+괄호 설명. 석사 연구 포트폴리오는 이전 `포트폴리오.pdf`가 있으므로 새로 만들지 않는다. 연구소 조교·SQL 교육 수료는 넣지 않는다.
- resum_summary 최신 `481dac1`: 이력서 4쪽·경력기술서 12쪽·경력 포트폴리오 22장·개인 프로젝트 포트폴리오 8장. 생성기 `tools/doc_builder/`(build_pptx_extra.py 추가). 기록 `references/CLAUDE_CROSSCHECK_APPLY_20261020.md`.
- 플랫폼 5곳 최신화는 job_agent 자동 저장(84f8a84) 기능으로 진행 예정(사용자 로그인 필요). 개인 Google Drive 사본 갱신은 남음.

## 플랫폼 저장 자동화·공통 이력서 최신화 (2026-10-21, 최신, Claude)

- 사이트 저장은 이제 로그인 후 자동(`ResumeSync.auto`, UI 동의 한 번). 결과는 `result/site_sync/auto-report.md`로 사후 검토. 반복 행(경력·프로젝트 추가)은 자동 생성하지 않음 → 사이트별로 기존 칸만 갱신.
- profile.json은 최신 이력서.md 기준으로 재작성(백업 profile.backup_20261021.json). 자기소개서 비움.
- 남은 일: 사용자 확인 후 5개 사이트 실제 실행(전용 브라우저 로그인 필요), 결과 보고서 공유. 공개 Vercel 배포 안 함.

## 시트 전체 저장·메일 30건 + Codex 지적 반영 (2026-10-21 새벽, 최신, Claude)

- 사용자: 배포 구조 유지, 조건 통과 공고 전체는 구글 시트, 메일은 30건 상한. 구현 완료(`alerts/sheet.py`, `deploy/sheets/job_alerts.gs`). **사용자가 할 일**: 시트 만들기 → Apps Script 붙여 넣기 → 스크립트 속성 `SHEET_TOKEN` → 웹 앱 배포 → `.env`에 `ALERT_SHEET_URL`·`ALERT_SHEET_TOKEN` (docs/job_alerts.md 4절). 설정 전에는 시트 단계만 건너뜀.
- 로컬 알림은 이제 후보 전부를 상세 확인(시간 수 분). 사이트 접속 제한(429·1015) 감지 시 그 회차에는 해당 사이트 중단. 캐치가 10-20 밤 이 PC를 일시 차단함 → 당분간 캐치 0건 가능.
- Codex 지적: 괄호형 경력·캐치 추천 영역은 수정. iframe 통합·캐치 목록 어댑터는 미구현(렌더러 불사용 결정). 상시채용은 사용자 정책대로 포함·표시 유지.
- 요청문·프롬프트는 파일로 저장하지 말고 채팅으로만 줄 것(사용자 요청, 기존 요청문 md 삭제함).

## 독립 검토 반영: 검색 누락 수정·서버 구독 본인 전용 (2026-10-20 밤, 최신, Claude)

- 사용자 결정: 지원 버튼 못 읽은 공고는 마감 근거가 있으면 "지원 버튼 미확인" 표시 후 포함, 경력은 요청 범위와 겹치면 포함, 헤드리스 렌더러 안 씀(삭제), 유료 서비스 안 씀·Vercel Hobby·본인 전용(이메일은 환경변수 `ALERT_ALLOWED_EMAILS`·Vault에만), 공개 배포 보류 중이며 공개 빌드는 구독 기본 제외.
- 결과: 저장 알림 메일 미발송 점검 26건(사람인·인크루트만) → 30건(상한) 잡코리아 12·사람인 10·인크루트 5·원티드 3. 캐치는 여전히 0(상세 9건 상태 미확인, JS 화면 추정). 독립 표본 21건 중 18 통과·2 기발송·1 검색 결과에 없음.
- 사용자: 이 작업이 끝나면 Codex에게 이어서 요청할 예정. Codex가 할 일(원격, 사용자 승인 후): `docs/server_alerts.md`의 할 일 1~6(Supabase 읽기 확인 → Auth 가입 끄기·본인 사용자 생성·OTP 8자리 → Vault 비밀 3개 → 001·002 SQL 적용·`alert_health()` 확인 → Vercel 환경변수 → `--with-subscriptions` 배포는 공개 배포 보류 해제 후). 키·주소를 채팅·문서·로그에 쓰지 말 것.
- 남은 것: 캐치 상세 상태 확인(정적 HTML 내장 데이터 조사), 메일 상한 30에 막혀 상세 미확인 후보가 많음(다음 회차로 넘어감·상한 조정은 사용자 결정), lease 토큰·같은 날 수정 누락(1인 운영이라 보류), 실제 Postgres SQL 테스트, Supabase 새 키 방식. 공개 Vercel 재배포 필요 여부: 로컬 UI 문구·링크와 공개 export 구성(구독 제외)이 바뀌었으므로 보류 해제 시 재배포 필요.

## 마감 공고 메일 후속 커밋·정밀도 표현 (2026-10-20 저녁, 최신, Claude)

- 사용자: 미커밋 job_agent 코드는 마감 공고 메일 버그 수정 후속이며 전부 커밋·푸시하라고 함. Claude가 리뷰 후 마감 판정 회귀(제목 위 마감 표시·메타 제목·div 추천 위젯)와 경력 None 오류를 고치고 커밋·푸시. 공개 배포는 하지 않음(요청 없음).
- 실제 건수 점검(메일 미발송): 저장 알림 기준 26건(상한 30), 사람인 20·인크루트 6, 잡코리아·캐치·원티드 0. 원문 확인 상한 100건에 걸려 255건 미확인. 이미 보낸 43건은 제외됨.
- 남은 결정: 기존 알림에 새 경력 기본값·지원 버튼 요건 적용(메일 감소 가능), 키워드 미일치 유지, 웹 가입형 알림·Vercel 렌더러는 미연결 초안. 실제 메일로 결과 건수 확인 필요.
- 이력서 표현: 통계 기법 이름은 풀어 쓰되 정밀도·재현율 같은 지표는 용어+괄호 설명으로 쓴다(사용자 요청). resum_summary `bd08468`. Codex 보고서 나머지 지적(H02·H03·M01·M03~M06·L01~L07) 반영 여부는 여전히 사용자 확인 대기.

## Codex 교차 검수 보고서·운영 수치 제거 (2026-10-20 오후, 최신, Claude)

- Codex가 resum_summary에 교차 검수 보고서 `references/CODEX_CROSSCHECK_20261020.md`(지적 17건)를 push함. 사용자 요청으로 제출 문서(이력서·경력기술서·포트폴리오)에서 회사의 실제 운영 건수(월 요청량·이관 건수·키 발급 성공 수·조직 조회 규모)와 내부 망 사정을 빼고 일반 표현으로 바꿈(`cce742e`). 보고서의 운영 수치 관련 지적 H01·M02·M07은 이때 반영했고, 두 검수 보고서의 같은 수치도 일반 표현으로 바꿈. 테스트 개수 같은 개발 검증 수치는 유지.
- 이후 Codex가 지적 일부 반영·연락처(사용자 제공)·고등학교 학력·AX 기간(2026.09~/10~)을 커밋. Claude가 통계 용어를 쉬운 말로 풀고(사용자 요청: 합의도 같은 말은 풀어 쓰기), 이전 문구로 남아 있던 PDF를 다시 만들어 push(`068c87e`, 3·10·22쪽 유지). 로컬 제출본·합본 갱신.
- 남은 일: 보고서의 나머지 지적(H02·H03·M01·M03~M06·L01~L07)과 빠진 경험 후보·확인 질문 반영 여부를 사용자에게 확인. 개인 Google Drive 사본은 여전히 10-19 버전. 비공개 저장소의 원자료(사용자 AX 정리·각 프로젝트 evidence)에는 원래 수치가 남아 있음.

## 포트폴리오 v4 개편·간접명 정리 (2026-10-20, Claude)

- 사용자 피드백: v3 포트폴리오는 색 박스가 많고 한 장 정보가 많아 난잡함. 상단 프로젝트 탭은 유지하고, 이전 포트폴리오(`공통 이력서 정리/포트폴리오.pdf`)처럼 흰 바탕에 설명 몇 줄 또는 그림 하나·키워드 중심으로. 제출 문서의 프로젝트는 간접명(사전 분류 모델·행위 이상 탐지·위험 기준값·API 게이트웨이·보안 업무 자동화)으로만 쓴다.
- 완료: resum_summary `6c6db7a` push. 새 생성기 `tools/doc_builder/build_pptx4.py`(흰 바탕·남색 한 색·‘프로젝트 / 주제’ 제목+한 줄 메시지·체크 2~4줄 또는 도식 하나, 상태는 글자)로 포트폴리오 22장 재생성, 경력기술서의 코드명 문단을 간접명으로, 디자인 규칙·README·Q15 갱신, 변경 기록 `references/CLAUDE_PORTFOLIO_V4_20261020.md`. 결과물 전체 코드명 0건(자동 검사), 이력서 3·경력기술서 10·포트폴리오 22·합본 32쪽.
- 로컬 `공통 이력서 정리/`의 경력기술서·포트폴리오·합본 교체, 이전본은 `_백업_20261020_포트폴리오개편전/`. 개인 Google Drive 사본은 아직 이전 버전(갱신은 사용자 확인 후).
- 사용자 요청으로 이 파일의 식별 정보를 지우고 최신 커밋을 다시 만들어 강제 push(`3be9ee0` → `f235f05`, develop·main 영향 없음).
- 다음: 사용자가 Codex에 교차 검수만 맡김(이어 쓰기 아님). Codex는 회사 쪽 원격 환경이라 노트북 파일을 못 보므로 비공개 resum_summary를 공용 통로로 씀(`7755650`): 가림 처리한 이전 문서·증빙 요약 `local_sources/`, 요청문 `notes/Codex_전달용_교차검수요청_20261020.md`, 보고서는 Codex가 `references/CODEX_CROSSCHECK_20261020.md`로 push할 예정. 같은 요청문의 로컬 사본은 `공통 이력서 정리/Codex_크로스체크프롬프트_20261020.md`.
- 사용자 요청으로 나중의 자기소개서 작성용 자료도 같은 저장소에 올림(`ef6a7e0`): `local_sources/applications/`(회사별 지원서 14, 스캔 9개는 Windows OCR 400dpi라 오인식 있음, 직무기술서·공고 3), `local_sources/cover_letters/`(업계별 자소서·면접 준비 10). 글자 추출본에서 연락처·주소·생년월일·연봉·나이·지원번호는 가림. 이어서 사용자 결정(비공개 저장소)으로 지원서 원본 15개(서한 HWP 포함)를 가리지 않은 채 `local_sources/files/applications/`에 추가(`6d7d423`). 사용자 문서 검토 → 서비스 공통 이력서 동기화 → 플랫폼 저장은 그대로 남음. 보안 관련 검토는 사용자가 직접 하므로 인계 문서·프롬프트에 넣지 않는다.

## 제출 문서 재작성 완료·Drive 업로드 (2026-10-19 밤, Claude)

- Codex가 비공개 `tabjun/resum_summary`를 프로젝트별로 재편(`25ad733`, Claude 전달용 요청문 `notes/Claude_전달용_검수와_경력문서_정리요청.md`). Claude가 이를 검수해 제출 문서를 새로 쓰고 `582ce75`로 push: 검수 보고·반영 대조표 `references/CLAUDE_REVIEW_20261019.md`, 이력서(3쪽)·경력기술서(10쪽) md/docx/pdf, 포트폴리오 22장 pptx/pdf/html/json/md, 생성기 `tools/doc_builder/`(원본: `content_resume.py`, `content_career.py`, `build_pptx3.py`).
- 주요 수정: AX 기간을 실제 진행 기준(보안 요청·조직 동기화 2026.05~, 제거키 2026.09~)으로, AX 상태를 구성 요소별로 표기, 원시 결과를 확인하지 못한 수치 제외, 학부·자격·산학·정규직은 로컬 이력서 원본으로 보완.
- 로컬 `etc/취업/공통 이력서 정리/`에 연락처 포함 제출본(`윤태준_경력이력서/경력기술서/경력포트폴리오_데이터사이언티스트.*`, 합본 PDF 32쪽) 배치. 개인 Google Drive 폴더 `윤태준 경력 문서 (2026-10-19)`에 원본 6개와 Google Docs 2·Slides 1 변환본 생성.
- 남은 일: 사용자 문서 검토 → 서비스 공통 이력서(`result/resume_profile/profile.json`, 현재 미검수 4개 항목)를 새 문구로 동기화 → 전용 브라우저 로그인 후 플랫폼 저장. 확인 질문: 팀 규모·담당 범위, 행위 이상치 탐지 종료 여부, AX 기간.

## 경력 이력서 최신화·플랫폼 적용·포트폴리오 (2026-10-19, Claude)

- 사용자 요청: 취업 폴더 `공통 이력서 정리`의 경력 이력서·경력기술서·포트폴리오를 private `tabjun/resum_summary`(2026-10-16) 기준으로 최신화. 직무명은 **데이터 사이언티스트**(ML 엔지니어 표기 금지). 이후 서비스 UI로 5개 플랫폼(원티드·사람인·잡코리아·캐치·인크루트)에 적용, 공고별 변환 결과를 README/result.md로 렌더링해 비공개 resum_summary(전체)와 공개 job_agent(익명 샘플) **둘 다** 푸시. 플랫폼 계정은 Chrome의 구직용 계정 프로필(연결된 Chrome 확장은 개인 메인 계정 프로필이라 사용 금지).
- 사용자 피드백: Codex식 명사 나열·내부 용어(무라벨·참조은행·하네스 등)·검증 메모 혼입으로 읽기 어렵고, P1의 부모·자식 분석/사유 출력/근거 제시 등 내용이 빠졌음. 흰 바탕 Word(표·선만), 프로젝트별 쪽바꿈 요구. 노션(포트폴리오 페이지)은 지금 수정 금지, 정리 완료 후 사용자가 적용.
- 완료(로컬, Git 무관): 새 Word `윤태준_경력이력서_데이터사이언티스트`(3쪽)·`윤태준_경력기술서_데이터사이언티스트`(7쪽, P1~P4·AX 각 쪽) docx/pdf, 작성 지침 `이력서_작성지침_업무자료정리.md`. 원본 백업 `_백업_20261019_이력서최신화전`. 17장 포트폴리오 PPTX 초안은 `_작업초안_포트폴리오`(요청문 용어 그대로라 문구 재작성 필요).
- 서비스 공통 이력서 `result/resume_profile/profile.json` 4개 항목 갱신·미검수(백업 `profile.backup_20261019.json`). 새 Word 문구로 다시 맞춘 뒤 사용자 검수 → 전용 브라우저 로그인 → 플랫폼 저장 순서. 아직 플랫폼 저장·푸시 없음.
- 확인 필요: AX 기간(`[기간 입력]`), API 게이트웨이(P4, 커밋 기준 2026.09) 이력서 포함 여부, 팀 규모·기여 범위.
- 후속(같은 날): 포트폴리오를 쉬운 문구 18장 PPTX/PDF(`윤태준_경력포트폴리오_데이터사이언티스트`)로 재작성, 합본 `윤태준 경력기술서 및 포트폴리오.pdf`(25쪽) 재생성. 사용자는 아직 내용 품질 불만족 → **Codex가 resum_summary를 프로젝트별 폴더(사전소명·행위 이상치탐지·지표 동적 임계값·API 게이트웨이·AX 3종)로 재편**하고 함수·API·구조까지 담은 표준 이력서/경력기술서/포트폴리오(md·slides.json·slides.html·디자인 요청문)를 커밋하도록 프롬프트 제공(`공통 이력서 정리/Codex_요청프롬프트_resum_summary_재정리.md`). 다음 Claude 작업: Codex 결과 pull → Word·포트폴리오 재생성, 필요 시 slides.json으로 사용자 Google Drive에 Google Slides 생성(사용자 제안), 이후 플랫폼 저장.

## 공고 알림 실사용 (2026-10-12, Claude)

- 사용자 .env에 Gmail SMTP 설정 완료(구직용 Gmail 인증됨). 테스트 알림 "데이터·AI 전반 (테스트)": 5개 플랫폼, 지역 "서울, 경기, 판교", 평일 08:00, 최대 30건, 켜짐. 30건 실제 발송 완료.
- 사용자 선호: 직무는 데이터 분석/데이터 사이언티스트/ML·DL/AI/통계/Python/R 등 폭넓게, 지역은 서울 전역+경기(성남·판교 선호), 그 외 지역 제외.
- 남은 개선 후보: 캐치 지난 마감(~MM/DD) 제외, 부트캠프/교육과정 제외(제외 키워드로도 가능), 플랫폼당 검색어 여러 개로 범위 확대.
- Git: 프로젝트별 저장소 분리는 사용자가 보류 지시(stock 서버 원격 브랜치·경로 연동). develop 승격 시 b05617b revert의 삭제 반영 주의 — 확인만 하고 변경하지 말 것.

## 공고 알림·적대적 리뷰 (2026-10-12, 최신, Claude)

- 사용자 요청: 전체 점검(Codex adversarial review) + 공고 탐색을 1회용이 아닌, 본인 인증 이메일로 플랫폼별 조건에 맞는 공고를 주기적으로 보내주는 등록 기능. 화면 확인이 필요하면 띄우기 전에 사용자에게 먼저 물어볼 것(사용자가 직접 로그인).
- 구현 완료(미커밋): `job_agent/alerts/`, `ui/static/alerts.js`, `/api/alerts`, `job-agent alerts`, `docs/job_alerts.md`. 로컬 PC 전용. 공개 웹 가입형 알림은 미구현(DB·메일 서비스·Cron 필요, 사용자 결정 필요).
- 남은 일: 사용자의 `.env`에 `ALERT_SMTP_*` 설정 후 실제 인증 메일/발송 확인, 필요 시 작업 스케줄러 등록. 실제 SMTP/Tavily 호출은 아직 검증 안 함.
- 리뷰 high: `/api/sync` 공유 방문자 접근은 수정함. `job_agent` 브랜치의 develop 대비 quantitative_trading/apple 대량 삭제 diff는 미해결 — develop 승격 전에 분리 필요, 사용자 결정 대기.

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
## 2026-10-15 최신: 공식 알림 설정 + 짧은 요약 메일

- 사용자 원래 의도는 사이트별 공식 맞춤 공고를 각 사이트 등록 이메일로 받게 설정하는 것. 별도 프로젝트 요약 메일도 유지하되 회사명 | 직무 | 공고 기간의 표로 간결하게 요청.
- alerts/mail.py, HTML MIME 대체 본문, 명시 기업/기간 추출(미확인 원문 확인), UI/문서 경로 구분 완료. 신규5+기존11+브라우저1 테스트 통과, 390/1280px 메일 레이아웃 통과. 이번 턴 실제 메일 발송 없음.
- 전용 브라우저 창 로그인은 사용자가 안 된다고 보고. 공식 플랫폼 조건/이메일 수신 저장은 아직 미실행. 사용자는 Chrome in ChatGPT 대안 문의. 공식 docs/chrome-extension 및 docs/browser 확인: 기존 로그인 Chrome은 설정 > Computer Use > Chrome 확장 연결 후 @Chrome, 내장 브라우저는 @Browser이며 별도 세션. 현재 대화에 해당 브라우저 도구 미연결. 로그인 도우미 종료, 보안 우회/쿠키 추출 금지.
- 기존 조건은 데이터·AI·통계/Python/R 등 폭넓은 직무, 서울·경기(판교 선호). 실제 사이트별 제공하는 메일 채널/조건을 확인한 뒤 설정하고 사이트별 검증 상태를 구분할 것. 이전 미커밋 변경은 보존, 커밋·푸시 없음.

## 2026-10-15 실제 공식 채용 메일 설정 결과

- 취업 Chrome 창이 확장에서는 taejun으로 표시되지만 사용자 스크린샷의 탭/계정과 일치. 사용자 정정 후 해당 창 사용.
- 경력 범위는 신입뿐 아니라 무관 및 1~5년 포함. 사람인 최종 검색메일과 인크루트 마이핏은 직무·서울/경기·경력 조건 저장/readback 완료. 사람인 이번 턴 임시 광범위 조건 수신 취소, 기존 구독 유지.
- 캐치 추천 채용 뉴스레터/잡코리아 AI추천/원티드 추천 포지션 이메일 ON 영속 확인. 추가 동의는 캐치·잡코리아 각각 명시 승인받음. 상세 조건을 해당 추천 메일에 강제하는 기능은 확인 못함; 5사이트 동일한 엄격 필터 완료로 표현하지 말 것.
- 등록 이메일·광고 수신 보존. 개인정보/계정 화면 증빙 ignored result/job_alerts/live-2026-10-15/. 실제 이메일 도착은 미검증. 다음 작업은 세 추천 기반 사이트의 별도 메일 조건 지원 여부 또는 기존 이력서 희망조건과의 연결을 검증하는 것.

## 2026-10-15 최신 요청: 코드 리뷰 + 흰 바탕 UI

- 사용자 후속 재확인: 완료한 작업 줄기/의미 있는 변경 묶음마다 검증 후 커밋·푸시까지 진행. 파일 수정마다 커밋하는 뜻은 아님. AGENTS.md/process.md에도 작업 종료 규칙으로 반영. 별도 보류 요청이 없다면 향후 반복 적용.
- 사용자는 녹색 Codex 유사 스타일 대신 흰 바탕에서 블록 구분이 예쁜 UI를 요청. UI/API·검수/저장·검색/알림·공용 엔진 검토 후 흰색/회색 카드, 남색 브랜드, 인디고 강조, 모바일 폼 배치와 포커스/현재 메뉴 접근성 반영. guide-overview 갱신; 기능 시연 이미지는 이전 디자인 표시.
- SMTP 보안 오타가 TLS 없는 로그인으로 이어지는 문제 차단, 제목 기반 공고 누락을 URL 기반 중복 처리로 수정. 다른 URL의 동일 공고가 중복될 수 있음을 문서화. 기존 저장 sent_titles는 무시, sent_urls 유지.
- 전체 135 tests 실패 없음/4 skip, 브라우저 8 실패 없음/2 skip, 메일8/알림12/튜토리얼3 통과. scoped Ruff/diff --check 통과. 가상 7화면 1440/390px overflow/JS 오류 없음. 증빙 ignored result/ui_review/white-2026-10-15/.
- 리뷰 문서 docs/code_review_2026-10-15.md. 남은 P2: 일반 검색 AI/R 부분 일치 오탐, 공용 엔진 미등록 도구 호출 ToolMessage 누락. 두 항목은 재현했으나 이번에는 문서화만 함. 외부 배포/실제 메일/API/채용사이트 변경/커밋/푸시 없음. job_agent 브랜치의 기존 다른 에이전트 변경 보존.

## 2026-10-15 최신: 큰 글자 + 기능별 아이콘 도식

- 사용자 요청으로 기본14→16px, 입력/라벨/안내16px·제목/메뉴/보조글자 확대와 줄 간격 개선. 첫 사용 상단에 아이콘 5단계 클릭 도식, 데스크톱 가로·모바일 세로. 공고 탐색은 독립 기능으로 표시. 기존 화면 이동만 수행, 저장 승인 정책 유지.
- UI 브라우저4, 알림 브라우저1, hosting5, 에셋3 통과. 7화면 × 5너비(320~1440px) 넘침/JS 오류 없음, 도식의 아이콘/이동 확인. 최초 누락 아이콘/알림 긴 안내문 넘침/기존 중복 테스트 선택자 수정 후 통과. hosting 기존 Ruff 경고3 유지, 예시 테스트 Ruff/diff check 통과.
- 새 증빙 ignored result/ui_review/readability-2026-10-15/. guide-overview 갱신. 앞 작업은 ad7e6aa로 푸시 완료했고, 이번 완료 변경도 job_agent에 커밋·푸시. 공개 배포 요청은 없음.

## 2026-10-15 최신: README 주소 명시

- README 상단에 공개 https://job-agent-resume-web.vercel.app/ 및 예시/로컬8765/PC연결도구 링크, 최신 큰 글자·아이콘 도식과 이미지 추가. 공개주소 GET 200 확인. 최신 UI는 아직 공개 배포 미적용으로 구분하고 별도 배포 문서 연결.
- 직전 UI 변경은 4909bd8로 푸시 완료. 이번 문서 변경도 검증 후 job_agent 커밋·푸시, 공개 배포는 하지 않음.

## 2026-10-15 최신: 실제 공개 사이트 UI 반영 완료

- 사용자가 색상/아이콘 변경이 안 보인다고 제보. 원인은 Git만 푸시하고 Vercel 별도 배포 누락. 공개 HTTP 재현에서 새 도식/CSS 없음 → allowlist export 54파일 dry-run 검수 → 기존 프로젝트 production 배포.
- https://job-agent-resume-web.vercel.app 는 현재 흰색/인디고·16px·아이콘5단계 최신 UI. READY dpl_57U9vdCQ32RPa8RZoHe6ez5KYuVz. HTTPS HTML/CSS/app.js 해시 일치, 실제 1440/390px 아이콘/단계 이동/검색API/리로드정리/저장소 비사용/넘침·JS오류 없음 확인. 유료공급자400 차단 확인, 실제 개인/포털/메일 작업 없음.
- README/배포문서 상태 갱신, 공개 화면 변경은 export검수·배포·고정주소 readback까지 완료 기준(process.md). Git 자동배포는 연결했다고 주장하지 말 것. ignored 배포본 result/hosting/ui-refresh-4909bd8/, 증빙 result/ui_review/production-2026-10-15/. 문서 변경도 커밋·푸시.

## 2026-10-15 최종 운용 원칙: 확정 커밋 즉시 서비스 반영

- 사용자가 서비스 변경 확정 커밋 후 바로 반영을 명시. 앞으로 검증 → 커밋·푸시 → allowlist export/검수 → 기존 Vercel 프로덕션 배포 → 고정 HTTPS 실제 확인을 별도 요청 없이 한 작업으로 완료한다. AGENTS.md/process.md에 반영. 사용자 보류는 따름. 개인정보/키/세션 업로드 금지 유지. 문서만 바뀌어 배포본이 같으면 재배포 불필요.
- 이 원칙은 에이전트 수행 절차이며 GitHub 자동배포가 설정됐다는 뜻은 아님. 현재 공개 UI는 최신 상태. 이번은 지침 문서만 변경해 커밋·푸시.

## 2026-10-15 최신: 공고 탐색 품질 개선

- 사용자 불만: 5개 플랫폼 직접 검색보다 회사/공고가 현저히 적음. 재현: UI 5도메인 합산12건 상한(가상50→12), 실제혼합10건/사이트별동일쿼리60건. 목록/다른 서비스/마감·중복/메타데이터누락 및 직무·지역·기술·연도 AND형 검색어가 병목. 기존 테스트는 수집품질 평가 부족.
- core/native_jobs.py 공개HTML 잡코리아·사람인 카드 우선(회사/직무 원문연결), 나머지/실패는 Tavily. core/postings.py 쿼리분리·20건×사이트×최대3쿼리·URL ID중복·명시마감·회사/키워드/지역·기업다양성 공통화. UI/알림/Agent1 적용. Agent1 하드코딩 May2026/고정직무/인크루트누락/마감문자오탐 제거. 경력 검증은 미구현으로 명시.
- 실제 2사이트 표본29건 회사명미확인0, 직접화면의 빗썸/퍼플아카데미/TMCK/메가스터디 등 복구 확인. 캐치/원티드/인크루트 원문·페이지네이션은 미구현이라 전체와 동등 주장 금지. docs/search_quality.md + examples/retrieval_audit --live/--replay, ignored result/search_quality/ 근거. 저장알림은 max30 유지, 실제메일/계정변경 없음. 다중직무 검색요청 최대15회로 늘 수 있어 UI/문서 안내.
- 전체154 테스트 실패0/4skip + Agent1신규1 통과; 최종원문5/검색12/알림14/메일8 재실행, 브라우저8 실패0/2skip, replay UI1440/390 정상. 공개는 여전히 수동 입력만. 서비스 영향 확정 커밋/푸시 후 allowlist export 기존Vercel 즉시 배포·실주소 확인 필요. 준비 export result/hosting/search-quality-20261015/.
- 최신 배포/푸시: ee3c9c9 기능커밋 후 즉시 Vercel READY dpl_9eWnXwFTBNJs6QfVaqBgWwM5WBjp. 최종export result/hosting/search-quality-final-20261015/ 56파일 검수. 고정주소 HTML/CSS/JS/PC연결ZIP 해시/새원문모듈 및 실API/1440·390 UI 확인 통과. 공개웹은 수동정리, 실제 검색개선은 로컬/업데이트PC연결도구용임을 구분. 배포기록 문서만 추가커밋·푸시.


## 2026-10-20 최신: 마감 공고 메일 혼입 수정

- 사용자 제보: 7월 게시 자체가 아니라 이미 접수 종료된 공고가 메일에 포함됨. 실제 발송 이력·현재 재검색에서 제보 직무의 캐치 링크 확인. Gmail 본문은 재인증 필요. 해당 캐치 원문은 조회 제한으로 현재 상태 미확인, 공개 타 플랫폼 동종 직무는 7월 마감 확인.
- 공통 postings 접수기간/괄호날짜/단독 마감문구 파서 보강. core/job_status.py 현재 공개 상세 원문 검증을 프로젝트 메일에 의무 적용: 마감/미확인 보류, 오래된 게시일은 제외 근거 아님. known route만 무쿠키 HTTP, 3MB/8초 제한, 4동시/8묶음/최대100개, 확인된 결과가 메일 상한 채우면 중단. 원문 상태가 바뀔 수 있어 지원 전 최종 검토는 사용자. UI/Agent1 목록 전체의 현재 모집 검증으로 설명하지 않음.
- 실제 검색266 후보 재생+최종 현재 원문72 점검 → 검색마감30/상세마감24/미확인17 제외·보류 → 진행근거30 선택. 메일 미발송, 저장 알림 파일 해시 유지. 증빙 ignored result/search_quality/deadlines-20261020/. 수신 이메일·광고 설정·sent_urls 건드리지 않음.
- 검증: 전체172 실패0/4skip, 최종 직무/메일/마감33·검색12·메일8·마지막 상태라벨10 통과. scoped Ruff/diff 통과. b32f0c8 커밋·푸시 후 result/hosting/deadline-check-final-20261020/ allowlist56파일 기존 공개 프로젝트 배포 완료. 고정 HTTPS HTML/CSS/JS/ZIP 해시·ZIP 최신 검증 소스 일치, 실제 API200/운영자 검색400 차단·1440/390px 예시2건·JS/넘침 확인. 운영자 알림은 로컬 다음 실행에서 새 코드 사용, 공개 Vercel에서는 계속 차단하며 갱신 PC연결ZIP을 제공. 개인 자료/설정/발송 기록·실제 메일 미변경.
