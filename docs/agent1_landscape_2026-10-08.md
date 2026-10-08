# Agent 1 비교 조사와 확장 설계

조사일: 2026-10-08. 아래의 확장 설계는 **아직 구현하지 않았다**. 현재 구현은 `job_agent/agents/job_hunter.py`와 `resume_reviser.py` 기준이다.

## 1. 결론

목표는 단순한 "내가 이 공고에 맞나?"가 아니라 **"이 회사와 역할을 선택할 이유가 있는가, 무엇을 확인해야 하는가, 내 실제 경험을 어떻게 연결할 것인가?"**다.

기업 분석 자체는 새롭지 않다. JobPT에는 기업 요약 에이전트가 있고, career-ops에는 회사 심층 조사 워크플로우가 있다. 우리 차별화 후보는 **한국 채용시장에 맞춘 근거 추적 가능한 지원 의사결정 리포트 + 검수된 마스터 이력서 + 여러 채용 양식으로의 연결**이다. 시장 최초라는 주장은 하지 않는다. [JobPT 구현](https://github.com/Pseudo-Lab/JobPT/blob/c2b7506b1d19ee14ff43ee9f1be12ee075885d3e/backend/multi_agents/prompts/summary_prompt.py), [career-ops deep](https://github.com/career-ops-hq/career-ops/blob/882004e083964c52b8e7130a7ba04a05ed72f057/modes/deep.md).

핵심 설계 판단:

- 적합도, 기업 위험, 경력 성장, 조건 충족, 정보 충분성을 하나의 점수로 섞지 않는다.
- 불확실한 정보를 그럴듯한 수치로 채우지 않고 `unknown`과 확인 질문으로 남긴다.
- 같은 회사라도 해당 팀·직무의 상황을 구분한다. 회사 평균 평점이 팀 문화의 증거는 아니다.
- 공개 기업 정보 수집에는 개인 이력서를 보내지 않는다. 개인화 분석에만 필요한 검수 사실을 사용한다.
- 다른 시스템의 도구·테스트 패턴을 선택적으로 참고한다. 전체 저장소나 에이전트 수를 그대로 가져오지 않는다.

## 2. 조사 범위와 검증 수준

사용자 지정 4개 저장소와 추가 3개 저장소는 기본 브랜치의 특정 커밋을 내려받아 파일 트리와 관련 구현/프롬프트/테스트 일부를 정적으로 읽었다. 추가 JobSpy·OinkAIJobSearch는 공개 저장소 설명을 검토했다. 서비스 6개는 공식 제품 페이지를 조사했다. 모든 파일·서비스·시장 후보를 빠짐없이 조사했다는 뜻은 아니다.

**외부 프로그램 실행, 의존성 설치, 실제 계정 가입·유료 사용, 성능 재현은 하지 않았다.** 테스트 파일이 있다는 사실과 테스트 통과는 다르다. README의 취업 성공 사례와 모델 성능 수치는 저자 보고이지 독립 검증 결과가 아니다. 원티드 에이전트 소개는 검색에 색인된 공식 페이지로 확인했으며 직접 열기는 403이었다. 캐치 상세 분석에는 접근 제한이 있었다.

정적 스냅샷은 Git 제외 경로 `result/research/2026-10-08/`에 보관했다. 개인 지원서·브라우저 인증정보는 외부 조사에 사용하지 않았다.

| 저장소 | 조사 커밋 | 확인 범위 |
| --- | --- | --- |
| Pseudo-Lab/JobPT | `c2b7506b1d19ee14ff43ee9f1be12ee075885d3e` | README, 검색/검색결합, 기업 요약 구현과 프롬프트, 파일 트리, frontend 라이선스 |
| jobai-project/jobai-ai | `c4acf89c52cea929ed21955334ea4a260afed2cd` | README, 사기업 점수 로직, FastAPI/임베딩/재순위 경로, CI |
| career-ops-hq/career-ops | `882004e083964c52b8e7130a7ba04a05ed72f057` | README, deep, 공고 활성 확인, 재공고 탐지, golden 평가 설명, 테스트 트리, LICENSE |
| MadsLorentzen/ai-job-search | `895c02191d28c8d88b8381ea68797ff6db599728` | README, 평가/웹 조사 규칙, 공고 식별 키, 회사 조사 캐시 테스트, LICENSE |
| noircir/job-scout | `9330f4a531b741b8b6708c3a242121a54068c07c` | 점수기, 기업 ATS 수집기, README 일부, 트리 |
| Orbitumaiopensource/Orbitapply | `d5948e8201f16dea47beb54a9efb6d88a33247be` | RECON 기업 조사 구현, 트리, LICENSE |
| juan-azabal/jobagent | `566879745d393e973a91d486869ae7424c977e33` | 사전 필터, 점수 출력 형식, full-CV ADR, 트리 |

## 3. 사용자 지정 저장소

### JobPT: 한국어 JD 검색과 기업 조사

이력서 기반 검색, 기업 요약, 서류 피드백, ATS 시뮬레이션을 결합한다. README의 대화 중 이력서 직접 반영은 예정으로 표시되어 있다. [프로젝트 설명](https://github.com/Pseudo-Lab/JobPT).

실제 검색 코드에는 의미 검색과 어휘 검색 순위를 RRF로 결합하는 경로가 있다. JD ID로 후보를 묶고 원문·URL·기업 메타데이터를 가져온다. 기업 요약은 LangGraph ReAct + Tavily MCP로 산업, 경쟁사, 제품, 문화, 진행 프로젝트를 조사하도록 구성한다. 다만 MCP 연결 실패 시 도구 없는 에이전트로 진행하는 fallback이 있어, 검색을 수행하지 않은 생성물이 조사 결과처럼 보이지 않도록 별도의 상태가 필요하다. [검색 코드](https://github.com/Pseudo-Lab/JobPT/blob/c2b7506b1d19ee14ff43ee9f1be12ee075885d3e/backend/get_similarity/nodes/search.py), [요약 코드](https://github.com/Pseudo-Lab/JobPT/blob/c2b7506b1d19ee14ff43ee9f1be12ee075885d3e/backend/multi_agents/agent/summary_agent.py).

**참고할 것:** 검색과 개인화 평가 분리, 공고 원문/메타데이터 유지, 제품·사업과 JD를 연결하는 조사 항목. **보류할 것:** 초기에 벡터 DB부터 도입하기, ATS 시뮬레이션 점수를 실제 합격 가능성처럼 표시하기.

### JobA!: 자동 수집 서비스와 공개 AI 서버를 구분

전체 서비스는 통합 수집·알림·지원 일정 관리를 설명하지만, 주어진 `jobai-ai` 저장소는 주로 임베딩·재순위·점수 산출 FastAPI 서버다. 이 저장소만으로 전체 수집/알림 서비스가 구현되었다고 판단할 수 없다. CI는 Docker build이며, README의 모델 평가 수치는 이번 조사에서 재현하지 않았다. [README](https://github.com/jobai-project/jobai-ai), [서버](https://github.com/jobai-project/jobai-ai/blob/c4acf89c52cea929ed21955334ea4a260afed2cd/ai-server/main.py), [CI](https://github.com/jobai-project/jobai-ai/blob/c4acf89c52cea929ed21955334ea4a260afed2cd/.github/workflows/ci.yml).

사기업 점수는 기술·임베딩·경력/우대 항목을 분해하고 부족 기술과 감점 이유를 반환한다. 그러나 가중치 합이 0.85이므로 감점 전 최대도 85점이다. `parse_jd`가 JD 전체에서 기술을 추출하고 `apply_gp`가 그 누락을 필수 기술 누락으로 취급한다. 우대 기술 하나만 없어도 60점 cap을 적용할 수 있다. 요건 구분 없이 복사하면 좋은 후보를 제외할 수 있다. [점수 코드](https://github.com/jobai-project/jobai-ai/blob/c4acf89c52cea929ed21955334ea4a260afed2cd/ai-server/scoring_jd.py).

**참고할 것:** 점수 근거·부족 기술의 구조화, 검색 후보 재순위. **가져오지 않을 것:** 검증되지 않은 가중치/임계값, 필수·우대 혼합 감점, 개인 시장과 무관한 NCS/공기업 흐름. ALIO는 기존 사용자 결정대로 제외한다.

### career-ops: 가장 가까운 종합 참고 대상

단순 매칭을 넘어 회사 선택, 맞춤 서류, 면접 준비와 지원 이력 관리까지 다룬다. `deep`는 AI 전략, 최근 움직임, 기술 문화, 예상 과제, 경쟁 구도, 후보자의 기여 방향을 포함하는 **조사 프롬프트 생성 워크플로우**다. 그것만으로 독립적으로 완결된 기업 조사 서비스가 실행된다는 뜻은 아니다. [README](https://github.com/career-ops-hq/career-ops), [deep 구현 명세](https://github.com/career-ops-hq/career-ops/blob/882004e083964c52b8e7130a7ba04a05ed72f057/modes/deep.md).

공고 활성 확인은 공개 ATS API를 먼저 시도하고, 결론이 없으면 Playwright로 확인하며 active/expired/uncertain을 구분한다. 재공고 탐지는 회사·직무의 유사성만 보지 않고 다른 URL, 서로 다른 관측 날짜, 제목의 지역/직급 차이와 aggregator 여부를 고려한다. **수집 실패는 마감이 아니고, 재공고는 허위 채용의 증거가 아니다.** 이 구분을 우리 설계에서 더 엄격히 유지한다. [활성 확인](https://github.com/career-ops-hq/career-ops/blob/882004e083964c52b8e7130a7ba04a05ed72f057/check-liveness.mjs), [재공고 코드](https://github.com/career-ops-hq/career-ops/blob/882004e083964c52b8e7130a7ba04a05ed72f057/detect-reposts.mjs).

Golden 평가 구조도 유용하지만 현재 설명은 합성 10건에 대한 기준 모델과의 일치도다. 사람 검수 정답에 대한 정확도나 채용 성과가 아니다. [평가 설명](https://github.com/career-ops-hq/career-ops/blob/882004e083964c52b8e7130a7ba04a05ed72f057/evals/README.md).

**우선 참고:** 활성 상태 확인, 단계별 도구 비용 제어, 지원 이력, 재공고의 오탐 방지 사례, 조사 결과를 면접 질문/서류 방향으로 연결. 전체 CLI·웹·플러그인 구조는 우리 Python 패키지로 이식하지 않는다.

### ai-job-search: 경력 방향과 사용자 주도 워크플로우

핵심은 Claude Code 명령·스킬 기반 운영이며, 덴마크 채용사이트용 TypeScript CLI와 Python 보조 도구가 함께 있다. 우리 LangGraph 서비스와 동일한 실행 형태는 아니다. [README](https://github.com/MadsLorentzen/ai-job-search).

평가 명세는 기술/실무 경험뿐 아니라 문화, 지역, 동기와 경력 방향을 다룬다. 사용자 제약과 필수 요건을 먼저 확인한다는 구조를 참고하되, 해외 취업 자격에 대한 일반화된 판정을 우리 로직에 그대로 넣지 않는다. 필수 조건 미확인과 실제 불충족을 구분해야 한다. [평가 명세](https://github.com/MadsLorentzen/ai-job-search/blob/895c02191d28c8d88b8381ea68797ff6db599728/.claude/skills/job-application-assistant/04-job-evaluation.md).

공고 식별 키는 비라틴 문자가 사라지는 ASCII 변환 문제를 인식한다. 기업 조사는 캐시 읽기/쓰기 명세와 테스트가 있으나, 해당 캐시 테스트는 Markdown 규칙의 존재를 검사한다. 실제 웹 조사 정확도·캐시 동작의 end-to-end 검증과 다르다. 웹 조사 명세에서 접근 실패를 expired로 보내는 부분 역시 우리는 unknown/blocked로 수정해야 한다. [식별 키](https://github.com/MadsLorentzen/ai-job-search/blob/895c02191d28c8d88b8381ea68797ff6db599728/tools/job_key.py), [캐시 테스트](https://github.com/MadsLorentzen/ai-job-search/blob/895c02191d28c8d88b8381ea68797ff6db599728/tests/test_company_research_cache.py), [웹 조사](https://github.com/MadsLorentzen/ai-job-search/blob/895c02191d28c8d88b8381ea68797ff6db599728/.claude/skills/job-application-assistant/09-web-research.md).

**참고할 것:** 지원 가능 여부와 선호도 분리, 성장/동기 평가, 조사 캐시, 초안→검토→수정, 공고별 서류 버전 보관. 한국 포털은 별도 어댑터가 필요하다.

## 4. 추가로 찾은 오픈소스

| 참고 대상 | 확인한 내용 | 우리에게 적용할 판단 |
| --- | --- | --- |
| [job-scout](https://github.com/noircir/job-scout) | Python 수집/평가/저장/요약 분리. 공개 Greenhouse/Ashby/Lever 수집기, 구조화된 점수·제약·지원 방향 | 가벼운 모듈 경계와 공개 ATS 어댑터 패턴. 필터/거주지 규칙은 특정 사용자 중심이므로 재사용하지 않음 |
| [Orbitapply](https://github.com/Orbitumaiopensource/Orbitapply) | 실제 RECON 코드가 문화·급여·뉴스·기술 검색 후 기업 JSON 생성 | 기회/위험을 따로 보여주는 출력 구상만 참고. 한글 전처리와 근거 계약은 새로 설계 |
| [jobagent](https://github.com/juan-azabal/jobagent) | 저비용 사전 필터, 근거를 포함한 strengths/gaps, 전략적 기여, 전체 CV 사용 결정 | 필터→개인화→심층 조사 순서, gap 추적, 작은 검수 프로필의 전체 문맥 사용 |
| [JobSpy](https://github.com/speedyapply/JobSpy) | 여러 해외 보드 공고를 공통 데이터 형태로 수집하는 라이브러리. 설명의 지원 사이트에 한국 우선 5개 플랫폼은 없음 | 해외 탐색을 확장할 때만 선택 후보. 한국 포털·개인 이력서 편집을 해결하는 라이브러리로 취급하지 않음 |
| [OinkAIJobSearch](https://github.com/Exdenta/OinkAIJobSearch) | README 기준 Telegram 알림, 중복 상태, CV 매칭과 시장 조사 명령 | 알림 요약/시장 수요 아이디어 참고. 코드·라이선스·시장 조사 품질은 심층 검증 전, 도입 후보 아님 |

추가 코드에서 발견한 주의점:

- **job-scout:** 점수 JSON은 `json.loads`로 읽지만 필드 타입/범위 계약 검증은 해당 점수기에 없다. Greenhouse `updated_at`을 `date_posted`에 넣는다. 수정일·게시일을 분리할 필요가 있다. [점수기](https://github.com/noircir/job-scout/blob/9330f4a531b741b8b6708c3a242121a54068c07c/scorer/score.py), [ATS 수집기](https://github.com/noircir/job-scout/blob/9330f4a531b741b8b6708c3a242121a54068c07c/scrapers/career_pages.py).
- **Orbitapply:** `sanitiseText`의 ASCII 중심 정규식이 한글 회사명/직무를 제거한다. 뉴스 검색 연도는 2024/2025 고정. 검색 URL은 프롬프트에 들어가지만 결과 JSON에 모든 주장별 출처가 강제되지 않는다. 기본 급여 0, remoteFriendly false는 미확인을 실제 값처럼 보이게 할 수 있다. "invented data를 estimated로 표시"하는 지시도 사실성 보장이 아니다. [RECON](https://github.com/Orbitumaiopensource/Orbitapply/blob/d5948e8201f16dea47beb54a9efb6d88a33247be/src/services/recon.js).
- **jobagent:** full-CV ADR는 작은 프로필을 RAG로 잘라 관련 경험이 빠진 문제를 설명한다. 이는 해당 프로젝트의 경험이지 모든 규모에 대한 정답은 아니다. 출력 `schemas/scored_job.json`도 예시 객체이며 정식 JSON Schema와 구분해야 한다. [ADR](https://github.com/juan-azabal/jobagent/blob/566879745d393e973a91d486869ae7424c977e33/docs/decisions/001-full-cv-over-rag.md), [출력 예시](https://github.com/juan-azabal/jobagent/blob/566879745d393e973a91d486869ae7424c977e33/schemas/scored_job.json).

## 5. 실제 서비스에서 참고할 사용자 경험

공식 페이지에 설명된 기능이며, 로그인 후 체험·성공률 검증은 하지 않았다. 제품 UI/데이터를 복제하는 것이 아니라 사용자 경험을 참고한다.

| 서비스 | 공식 설명에서 확인한 기능 | 반영 방향 |
| --- | --- | --- |
| [Teal](https://www.tealhq.com/tools/job-tracker) | 공고 북마크, 단계 관리, JD 키워드, 체크리스트, 연락처와 후속 연락 | 공고를 찾은 뒤 "다음 할 일"과 서류 버전을 연결 |
| [Huntr](https://huntr.co/product/job-tracker) | Kanban, 활동 이력, 공고별 문서/연봉/연락처, 위치, 탐색 지표 | 단순 추천 목록보다 지원 진행 이력과 비교 가능한 조건을 유지 |
| [Simplify Copilot](https://simplify.jobs/copilot) | 여러 ATS 폼 자동 입력, 맞춤 답변, 제출된 지원의 기록 | Agent 3와의 연결 참고. 입력/저장/제출 상태를 분리하고 증거 없이 완료 표시 금지 |
| [원티드 에이전트](https://www.wanted.co.kr/ai/agent/intro) | 조건/경력 기반 포지션 탐색과 공고별 이력서 코칭 | 국내 경쟁 기준. 우리 적합도 지표를 합격 확률로 포장하지 않기 |
| [캐치 기업분석 예시](https://www.catch.co.kr/Comp/AnalysisCompView?ID=4935) | 사업 방향, 성과, 경쟁/SWOT, 채용 가치, 면접, 현직자 만족도 항목 | 기업 개요가 아니라 지원서/면접에 활용 가능한 설명 구조. 접근 제한 본문은 재배포하지 않음 |
| [Levels.fyi](https://www.levels.fyi/about) | 회사·레벨·지역별 보상/직급 비교와 제출 데이터 검증 설명 | 연봉 총액뿐 아니라 직급·기본급·변동급·주식·지역·표본/시점을 나눠 비교 |

## 6. 우리 현재 구현의 실제 부족한 점

아래는 외부 평가가 아니라 현재 `job_agent/agents/job_hunter.py`를 직접 읽은 결과다.

| 현재 상태 | 문제 | 먼저 바꿀 것 |
| --- | --- | --- |
| 검색/프롬프트 날짜가 2026-05-11/2026년 5월로 고정 | 오늘의 공고 탐색과 불일치 | 실행 시각과 사용자 검색 기간 주입 |
| `role` 인자가 있지만 DA/DS 고정 검색 | 일반 직무 입력을 지원하는 것처럼 보일 수 있음 | 현재 범위를 명시하고 직무 설정을 실제 검색에 연결 |
| 내용에 "마감"이 있으면 삭제 | "마감일 10월 31일"도 제외 가능 | 원문 기반 open/closed/unknown/blocked, 기한과 시간대 구분 |
| URL 문자열로만 중복 제거 | 동일 공고의 추적 URL/교차 게시를 중복 처리 | 사이트 posting ID, 정규 URL, 회사·팀·지역·직급 보조 비교 |
| 재무/평판 도구가 snippet 내용만 반환 | URL·제목·게시일이 소실 | 원문 출처, 조사일, 주장 근거 유지 |
| 프롬프트가 매출/영업이익·별점을 필수 요구 | 미확인 숫자를 채울 압력 | 자료 없음 허용, 단위/기간/리뷰 표본 분리 |
| Hunter 입력은 경력·지역·키워드 | 검수된 경험 근거와 사용자 가치관을 평가에 직접 연결하지 못함 | Agent 2의 검수 프로필 + 명시 선호/제약 연결 |
| 단일 도구 루프 + Markdown | 명시적 단계별 상태·실패·근거 계약 부족 | 구조화 결과를 먼저 저장하고 Markdown은 표시 계층으로 생성 |

이 문제를 고치기 전 기업 분석 항목만 늘리면 오류와 비용도 늘어난다. 기존 실행 기록은 확장 기능의 완료 증거가 아니다.

## 7. 제안하는 지원 의사결정 리포트

각 공고에서 다음 질문에 답한다. 이는 외부 기능을 참고한 **우리 설계 제안**이다.

| 분석 축 | 제공할 정보 | 반드시 표시할 한계 |
| --- | --- | --- |
| 공고 유효성/지원 가능 | 공식 JD, 게시/수정/마감, 직무·경력·지역·고용 형태, 필수/우대 | blocked/unknown을 closed로 바꾸지 않음 |
| 실제 경험 적합성 | 요구사항별 내 근거, 직접/전이 가능 경험, 확인 필요/부족 항목 | 자기소개 문장과 실제 경험을 구분, 기술 키워드만으로 숙련 판정 금지 |
| 사업/재무 안정성 | 사업 모델, 주요 제품/고객, 공시 재무 추세, 공식 투자/조직 변화 | 연결/별도·연도/분기·단위, 공시 없음을 부실로 해석하지 않음 |
| 직무의 실체 | 제품/분석/운영/영업 지원 등 실제 업무 비중, 팀 기술 환경·문제 | 공고/기술 블로그 기반 추정과 현직자 확인 사항 분리 |
| 성장/경력 방향 | 내 목표와 연결되는 다음 경험, 전이 가능한 역량, 역할의 장단점 | 사용자가 정하지 않은 목표·선호를 만들어내지 않음 |
| 보상/근무 조건 | 공개 범위, 직급, 고용 형태, 수습, 근무 위치, 재택/출장/온콜 | 시장 평균과 해당 공고 오퍼를 구분; 없는 급여는 null |
| 문화/리스크 | 날짜·표본·직군별 리뷰 신호, 상반된 정보, 조직 변동 | 리뷰는 주관적 신호; 회사 전체 평점으로 팀을 단정하지 않음 |
| 지원/면접 전략 | 실제 경험에서 강조할 이야기, 검증 질문, 지원 전 할 일 | 채용 의도와 합격률을 단정하지 않음 |

정보가 풍부한 공고만 상위에 올리면 비공개 정보가 많은 중소기업에 불리하다. **정보 충분성과 선호 순위는 별도 표시**한다. 추론과 확인 질문도 무조건 부정 신호로 계산하지 않는다.

출력 구성은 짧은 비교표 + 공고별 근거 상세 + 면접 확인 질문 + 서류 수정 방향이다. "지원 권장/조건 확인 후 판단/보류"는 사용자의 선호 기준에 따른 권고이며 확정 판정이 아니다. 권고 사유와 미확인 항목을 함께 보여준다.

## 8. 출처와 사실 계약

아래는 도입할 데이터 구조의 예시다. 현재 코드에 추가되었다는 의미는 아니다.

```text
JobPosting: source, posting_id, canonical_url, company_id, title,
            required[], preferred[], posted_at, updated_at, deadline,
            observed_at, status, status_reason, document_hash
SourceRecord: id, url, title, publisher, published_at?, retrieved_at,
              source_type, excerpt_or_locator, fetch_status
Claim: id, statement, source_refs[], fact_or_inference, confidence_reason,
       period?, unit?, entity_scope?, contradicting_refs[], verification_question?
FitFinding: requirement_ref, candidate_evidence_refs[], match_type,
            gap_or_unknown, reason
DecisionBrief: eligibility, fit_findings[], company_claims[], career_tradeoffs[],
               conditions[], questions[], recommendation, missing_information[]
```

확인된 사실에는 해석 가능한 원문 근거가 필요하다. `confidence_reason`은 수집 성공/실패·출처 권위·관련성·자료 시점·상충 여부를 설명하며 모델의 자기확신 점수가 아니다. 출처 URL이 있다는 것만으로 주장이 입증되지는 않는다. 사람이 표본 검수한다.

후보자 근거는 Agent 2의 기존 `source_id`/문단 참조를 유지한다. 회사 공시 근거와 후보자 경험 근거는 별도의 namespace를 쓴다. 찾지 못한 회사 수치·리뷰 평점·연봉은 null/unknown으로 남기며 후보자 경험은 생성하지 않는다.

## 9. 수집 경로와 캡슐화

한국 우선 대상은 캐치·잡코리아·사람인·원티드·인크루트이며 ALIO는 추가하지 않는다. 검색 노출 확인과 로그인 이력서 편집은 별도 기능이다.

회사 자체 사이트는 전부 브라우저만 필요한 것은 아니다. Greenhouse는 Job Board API, Lever는 공개 게시 API, Ashby는 공개 Job Postings API를 문서화한다. **공개 공고 조회와 개인 지원서 편집/제출 권한은 다르다.** 회사가 해당 ATS를 사용할 때의 선택 경로이며 한국 5개 보드 지원을 의미하지 않는다. [Greenhouse](https://docs.greenhouse.io/job-board.html), [Lever](https://github.com/lever/postings-api), [Ashby](https://developers.ashbyhq.com/docs/public-job-posting-api).

수집 우선순위 제안: 허용된 공식 공개 API → 공식 채용 HTML/구조화 데이터 → 웹 검색으로 URL 발견 → 허용된 브라우저에서 사용자가 연 페이지 확인. 약관·접근 정책과 수집 빈도를 검토한다. 인증/유료 벽·차단을 우회하지 않고 사용자가 제공한 원문 또는 수동 확인으로 전환한다. robots 허용만으로 모든 사용이 허가되었다고 보지 않는다.

국내 기업 재무는 OpenDART의 공시·재무 데이터부터 검토한다. 모든 기업의 자료가 있는 것은 아니다. 법인 동명이인·브랜드/자회사 매핑과 연결/별도 기준을 확인한다. 재무 신호는 커리어 의사결정 자료이지 투자 권고나 부도 예측이 아니다. [OpenDART 공식 소개](https://opendart.fss.or.kr/intro/main.do).

새 모듈은 필요할 때 작게 추가한다. 권장 책임 경계(예정):

```text
job_agent/jobs/           공고 모델, 수집 어댑터, 원문/활성 확인, 식별/중복
job_agent/company/        회사 식별, 출처 자료, 재무/사업/팀 신호
job_agent/assessment/     요건-근거 매핑, 제약, 경력 방향, 리포트 계약
job_agent/agents/         job_hunter 조정, resume_reviser 서류 수정
job_agent/documents/      기존 검수 마스터/개인 사실, 변경 없이 재사용
job_agent/sites/          기존 회사 URL 등록/양식 변환, Agent 3에 위임
```

각 서비스가 fetch·검증·저장을 내부에서 처리하고 조정자는 좁은 결과 계약만 사용한다. 같은 공고 수집을 서류 작성기와 회사 분석기가 반복하지 않는다. 기능별 클래스를 늘리기보다 실제 외부 I/O와 데이터 수명 경계를 캡슐화한다. 현재 `LangGraphAgentEngine`을 유지하고 전문 단계가 필요할 때 그래프로 분리한다.

## 10. 도입 순서와 검증

| 순서 | 반영 내용 | 통과 기준 |
| --- | --- | --- |
| P0: 신뢰성 기반 | 날짜 고정 제거, 원문/활성 상태, 필수/우대 분리, 회사/공고 식별, 출처 보존, unknown 허용 | 한국어 경계 사례, 마감일 포함 열린 공고, 차단 페이지, 동명 기업, URL 중복의 결정적 테스트 |
| P1: 의사결정 | 검수 마스터 연결, 근거별 적합성, 국내 사업/재무·팀·조건·성장, 면접 확인 질문 | 사람 검수 표본에서 각 사실 출처/시점/개인 근거 추적; 미확인 수치 생성 없음 |
| P2: 반복 운영 | 회사 조사 캐시, 공고별 문서 버전/지원 상태, 변화·새 공고 요약, 사용자 피드백 | 재실행 중복 방지, 자료 갱신/원문 변경 처리, 저장/제출 확인 없는 완료 전환 금지 |
| P3: 검색 고도화 | 규모가 커질 때 BM25+의미 검색/재순위, 해외 ATS 추가 | 단순 검색 baseline보다 인간 평가 relevance 개선, 비용/지연 비교 |

평가 자료는 사람 검수한 공개/합성 JD로 시작한다. 합성만으로 실제 성능을 주장하지 않는다. 필수/우대 오분류, 경력 범위, "경력무관", 날짜/시간대, 게시/수정일, 한글 회사명, 상시채용, 자료 없는 비상장 기업, 상충된 리뷰, 재공고/복수 지역을 포함한다.

측정할 것: 열린 공고 판정 precision/recall, 요건 추출·법인 연결 오류, 주장-출처 일치율, 근거 없는 생성 수, 미확인 표시율, 사용자 선택 이유, 비용/지연. 미확인 표시만 늘려 일치율을 높이지 않도록 정보 coverage도 함께 측정한다. 개인 지원 결과는 전략 개선 자료로 쓰되 작은 표본의 합격률을 모델의 예측 정확도로 보고하지 않는다.

## 11. 재사용과 라이선스 확인

코드 복사는 이번 작업에서 하지 않았다. 아이디어 참고와 코드/문서 복제는 구분한다. 라이선스 판단은 아래 스냅샷의 파일 확인 범위이며 도입 전 대상 파일·의존성·데이터 사용 조건을 다시 확인한다.

| 대상 | 확인 결과 | 재사용 판단 |
| --- | --- | --- |
| career-ops | 루트 LICENSE MIT, README에 상표 정책 별도 | 저작권/허가문 보존과 의존성 검토 후 선택 복사 후보. 이름/브랜드 복제하지 않음 |
| ai-job-search | 루트 LICENSE MIT | 일부 도구/테스트 패턴의 선택 도입 후보. 해외 개인 규칙은 분리 |
| JobPT | 루트 포괄 LICENSE 없음, `frontend/LICENSE`는 Apache-2.0, PDF.js 등 제3자 라이선스 별도 | frontend 라이선스로 backend/연구 코드까지 허가되었다고 추정하지 않음. backend 복사 보류 |
| jobai-ai | 조사 트리에 포괄 LICENSE 없음 | 공개 열람과 재배포 허가는 별개. 코드/가중치 복사 보류 |
| job-scout | README는 MIT라고 표시, 별도 LICENSE 파일 없음 | 저작권/허가 조건 명확화 전 코드 도입 보류 |
| jobagent | 조사 트리에 포괄 LICENSE 없음 | 설계 참고, 코드 복사 보류 |
| Orbitapply | `OrbitumAI Free License` 제목, 본문은 MIT형 허가/면책 문구 | 표준 MIT 이름으로 단정하지 않고 원문 조건 확인. 한국어/근거 문제 때문에 코드 도입 비추천 |
| JobSpy | 공개 저장소 MIT 표시 | 선택 의존성 후보, 설치 버전 LICENSE와 각 사이트 정책 별도 확인 |
| OinkAIJobSearch | 이번 범위에서 LICENSE 원문 미검토 | 도입 전 추가 검토 |

외부 전체 프롬프트/규칙·install script·allowlist를 가져오지 않는다. 로컬 `.agents/` 등에 설치하는 행위도 필요할 때 별도 검토한다. 공개 채용/기업 페이지의 숨은 지시문은 자료로만 다루고 도구 제어에 반영하지 않는다.

## 다음 구현 단위

가장 작은 시작은 **공고 원문/날짜/상태와 출처 계약을 확보하는 P0**다. 그 다음 "JD 요구사항 ↔ 검수 이력서 근거 ↔ 회사/팀의 검증된 상황 ↔ 확인 질문"을 하나의 리포트로 연결한다. Agent 2/3를 대체하지 않고 이미 구현한 근거·양식 연결을 재사용한다.
