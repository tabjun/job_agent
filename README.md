# 🚀 이력서 자동화 에이전트: AI 커리어 어시스턴트 (LangGraph + GPT/Gemini)

이 프로젝트는 **LangGraph** 기반의 전문 에이전트들이 **공고 탐색 → 맞춤 서류 생성 → 마스터 이력서 표준화 → 채용사이트 동기화**의 흐름을 처리하는 이력서 자동화 시스템입니다.

**핵심 아이디어:** 공고 탐색과 서류 생성은 AI가 담당하고, **최종 검토와 저장·제출은 사용자가 직접** 수행합니다(Human-in-the-loop). AI는 사실에 근거한 초안까지만 만들고, 사람의 확인 없이 대신 제출하지 않습니다.

## 🏗️ 시스템 아키텍처

![이력서 자동화 에이전트 구조](images/project_archi.png)

역할 분리(Separation of Concerns)를 통해 각 단계의 전문성과 정확도를 높였습니다. 아래 표의 **구현 상태**는 과장 없이 현재 코드 기준으로 표기합니다.

### 1. 🔍 Agent 1 — Job Search & Resume Reviser (`job_agent/agents/job_hunter.py`, `job_agent/agents/resume_reviser.py`)
*   **역할**: 채용공고 검색 · DART 재무/평판/JD 분석 · 공고별 이력서·자소서 수정.
*   **구현 상태**: **실행 가능.** 공고 검색·기업 분석·리포트 저장 루프의 과거 GPT 실행 기록이 있습니다. GPT-6 Luna 전환의 검증 범위는 아래 모델 안내를 참고하세요. 이력서/자소서 수정은 `job_agent/agents/resume_reviser.py`에 구현.
*   **데이터 출처 현황 (사실성 관련 중요)**:
    *   현재 우선 대상은 **캐치·잡코리아·사람인·원티드·인크루트**입니다. ALIO 연동은 진행하지 않습니다. 이력서 편집은 로그인한 실제 화면의 DOM을 조사하여 Playwright로 연결합니다. 채용정보 조회 API와 개인 이력서 편집 기능은 별개입니다.
    *   민간 사이트(원티드·사람인·잡코리아·점핏·캐치 등)는 별도 API가 아니라 **Tavily 웹 검색 + `site:` 필터**로 best-effort 수집하며, 누락·중복·신선도(마감 여부) 한계가 있습니다.
    *   재무(DART)·평판(잡플래닛) 정보도 공식 API 결합이 아니라 Tavily 검색 결과 요약이므로, 수치는 **참고용**이며 단정하지 않습니다.
*   **산출물**: 선별된 정예 공고 리포트(`result/job_search_results.md`), 맞춤 자소서·이력서 전략(`result/revised/`).

### 2. 🗃️ Agent 2 — Master Resume Builder
*   **역할**: 경력/프로젝트/기술스택을 표준화하여 `master_resume.yaml` 단일 원천으로 관리(사실 기반 이력 관리).
*   **구현 상태**: **부분 구현.** `job_agent/documents/source.py`로 원문을 추출하고, `job_agent/documents/library.py`로 명시 선택한 DOCX의 문단 근거를 연결한 검수 초안을 JSON/Markdown으로 컴파일합니다. 완전 자율 정규화·문장 사실성 판정은 아직 지원하지 않습니다.
*   **의도**: Agent 1이 공고별로 이력서를 수정할 때, 매번 원본을 다시 파싱하지 않고 이 표준 이력서를 근거(single source of truth)로 사용합니다.

### 3. 🔁 Agent 3 — ResumeOps Sync Agent (`job_agent/agents/site_resume.py`, `job_agent/browser/mapper.py`, `job_agent/browser/connector.py`, `job_agent/browser/filler.py`)
*   **역할**: 캐치/잡코리아/사람인/원티드/인크루트 양식 변환 · Playwright 기반 **반자동** 입력.
*   **구현 상태**: **부분 구현.** 입력 패키지 생성, DOM 추출·연결, 검수된 기존 텍스트 필드 입력 실행기가 있습니다. 로그인과 최종 저장은 사용자가 합니다. 반복 항목 생성·태그·custom 선택 UI는 사이트별 구현이 추가로 필요합니다. 실제 계정 입력 범위와 저장 검증 여부는 [작성 기록](docs/resume_authoring.md)에 구분했습니다.
    *   `job_agent/agents/site_resume.py`: 이력 데이터를 사이트 양식에 맞춘 JSON/Markdown 패키지로 변환 → `result/site_resumes/`.
    *   `job_agent/browser/mapper.py`: 채용 사이트 입력 화면에서 `input`/`textarea`/`select`/버튼/라벨/selector 추출.
    *   `job_agent/browser/connector.py`: 패키지 필드와 실제 DOM selector 후보를 연결한 매핑 계획 생성.
    *   `job_agent/browser/filler.py`: 개별 검수 표시가 있는 필드만 검증/입력. 자동 저장·제출 클릭은 없음.
*   **가드레일**: 연락처·주소·희망연봉 등 민감 필드는 사용자가 명시한 경우에만 채우고, `knowledge/`와 사용자가 제공한 사실에 없는 경력·수치·자격은 만들지 않습니다.

### 👤 Human-in-the-loop
*   사용자가 최종 확인하고, **저장/제출은 직접 수행**합니다. AI는 대신 제출 버튼을 누르지 않습니다.

#### Agent 3 실행 예시
```bash
# 정적 폼 스냅샷 (공개 URL·로그인 리다이렉트·접근 가능 여부)
python -m job_agent form-map --mode static

# 브라우저를 열어 직접 로그인 후 폼 요소를 JSON으로 저장 (사용자가 로그인)
uv sync --extra browser
.\.venv\Scripts\python.exe -m job_agent form-map --mode playwright --sites catch --headed --interactive

# 이력서 패키지 필드 ↔ DOM selector 후보 연결
python -m job_agent form-connect --package result/site_resumes/example.json --form-map result/site_form_maps/wanted_playwright_xxx.json

# 검수한 mapping 항목에 "approved": true 표시 후 실행 (기본은 검증만)
python -m job_agent form-fill --site wanted --package result/site_resumes/example.json --mapping result/site_field_mappings/example.json
# 실제 입력은 --apply 추가 후 터미널에서 APPLY 입력
```

기본 대상 순서는 캐치 → 잡코리아 → 사람인 → 원티드 → 인크루트입니다. `--interactive`에서는 로그인·편집 화면 이동 후 터미널에서 Enter를 누르면 해당 사이트의 열린 탭과 iframe을 수집합니다. 경력/프로젝트 추가 폼이나 팝업을 열고 다시 Enter를 눌러 여러 상태를 기록한 뒤 `q`로 종료합니다. 실제 화면에서 확인한 URL은 `--sites wanted --url <URL>`로 지정할 수 있습니다. 실제 화면 조사 결과는 [사이트별 관찰 기록](docs/site_form_observations.md)에 있습니다.

전용 로그인 프로필은 `result/browser_profiles/<site>/`, 스냅샷은 `result/site_form_maps/`에 보관하며 Git에서 제외합니다. 평소 Chrome 프로필과 별개라 전용 브라우저에서는 첫 로그인이 필요합니다. 입력값 미리보기는 기본 제외이며 `--include-values`로 선택할 수 있습니다. 비밀번호와 hidden 입력값은 항상 제외합니다. 셀렉터 후보는 중복 대상·동점·글자수 초과를 표시하는 검토용 계획이며 자동 저장·지원 동작은 없습니다. 인증 상태 관리 방식은 [Playwright 공식 문서](https://playwright.dev/python/docs/auth)를 참고합니다.

---

## 🛡️ 가드레일 (Guardrails) 및 환각 방지 전략

AI 에이전트가 흔히 저지르는 '없는 경력 지어내기'나 '영혼 없는 찬양'을 방지하기 위해 다음과 같은 장치를 마련했습니다.

### 1. `/knowledge` (나의 사실적 데이터베이스)
*   에이전트는 이 폴더 내의 파일들(`resume.txt`, `career.docx` 등)에 명시된 프로젝트, 기술, 경력 사항만 사용할 수 있습니다.
*   이력서에 없는 기술이나 경력이 JD에 있다고 해서 이를 거짓으로 추가하지 않도록 프롬프트 수준에서 엄격히 통제됩니다.

### 2. `/more_info` (나의 커리어 철학 및 가이드라인)
*   **작성 스타일**: "간결하고 데이터 중심적인 문체", "인사이트 도출을 강조하는 서술" 등 사용자가 원하는 톤앤매너를 설정합니다.
*   **가치관 주입**: 단순한 기업 찬양 대신, 사용자가 평소 중요하게 생각하는 직업적 가치(예: '효율적인 협업의 즐거움', '기술적 난제 해결의 쾌감')를 자소서의 메인 테마로 활용하게 합니다.

---

## 🤖 에이전트 작업 지침

서버와 로컬 Claude/Codex가 같은 작업 기준을 공유하도록 루트 Markdown 문서를 추적합니다.

*   `AGENTS.md`: 강제 규칙, 실행 경계, 세션 시작 규칙
*   `skills.md`: 기술 철학, 에이전트 설계 기준, 권장 워크플로우
*   `process.md`: 현재 운용 절차와 반복 작업 방식
*   `history.md`: 의미 있는 변경 이력
*   `conversation_l2_cache.md`: 최근 사용자 의도와 제약의 압축 캐시
*   `CLAUDE.md`: 로컬 Claude 계열 도구용 진입 문서

`.agents/`, `.codex/`, `.claude/settings.local.json`은 로컬 스킬과 플러그인 설정이므로 Git에 포함하지 않습니다.

---

## 🧪 문서 파싱 및 MCP 연동 (`kordoc`)

실제 DOCX 입력 테스트는 LLM/kordoc 없이 `job_agent/documents/source.py`로 원문과 문단 근거를 추출할 수 있습니다. 이번 원본 양식의 명시된 경력/소개 경계를 사용하며, 다른 양식은 검수가 필요합니다.

```powershell
.\.venv\Scripts\python.exe -m job_agent source --source 'knowledge/윤태준 경력 이력서.docx'
$env:RESUME_TEST_DOCX = 'knowledge/윤태준 경력 이력서.docx'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

개인 결과물은 Git에서 제외하는 `result/source_resume_test/`에 저장합니다. [실제 입력 테스트 기록](docs/real_source_test.md)에 사이트별 결과와 미검증 범위를 구분했습니다. 원티드는 포커스 이동 시 자동 저장되므로 최종 버튼을 누르지 않아도 내용이 전송될 수 있습니다.

여러 자료로 공통 이력서를 작성할 때는 파일을 명시적으로 선택합니다. 폴더 전체를 자동 수집하지 않아 주민등록·계약·금융자료 등이 섞이지 않도록 합니다.

```powershell
python -m job_agent library extract --source "<최신 경력 이력서.docx>" --source "<경험기술서.docx>"
python -m job_agent library build --corpus result/resume_library/corpus.json --draft result/master_resume/reviewed_draft.json
```

검수 초안의 `blocks`에는 `field`, `text`, `evidence`를 작성합니다. `evidence`는 `source_id`와 `paragraph_indices`로 원문을 참조합니다. 컴파일러는 원본 SHA256, 추출문, 참조 문단의 존재를 검사하지만 의미상 사실 여부를 자동 판정하지는 않습니다. 출력은 `result/master_resume/master_resume.md` 및 JSON과 사이트별 공통 입력 패키지입니다. custom 선택 UI/반복 항목은 사이트별 추가 검수가 필요합니다. [최신 실제 작성 범위](docs/resume_authoring.md)를 참고하세요.

본 프로젝트는 **kordoc**을 활용하여 HWP, PDF, DOCX 등 다양한 형식의 문서를 마크다운으로 변환하여 학습합니다.

### 1. kordoc 설정 (MCP 연동)
AI 에이전트(Gemini CLI, Cursor 등)가 문서를 직접 읽을 수 있게 하려면 다음 명령어를 실행하세요.
```bash
npx -y kordoc@latest setup
```
*   설정 과정에서 사용하는 에이전트(예: Gemini CLI 또는 VS Code)를 선택하면 해당 도구의 설정 파일이 자동으로 업데이트됩니다.

### 2. Resume Reviser에서의 활용
`UserContextLoader`는 DOCX를 로컬에서 읽고, HWP/PDF는 `kordoc`으로 변환하여 `knowledge/` 폴더 내의 모든 문서를 실시간으로 파싱합니다. 따라서 사용자는 파일을 별도로 변환할 필요 없이 원본 파일을 그대로 넣어두면 됩니다.

---

## 🚀 사용 방법

에이전트 실행 시 `1`은 Gemini, `2`는 OpenAI를 선택합니다. 아래 OpenAI 모델 안내는 2026-10-07 공식 문서 확인 기준입니다.

*   **GPT-6 Luna (`gpt-6-luna`)**: 이 프로젝트의 OpenAI 기본 모델입니다. 공식 문서상 비용 효율적인 반복 작업용 모델이므로 공고 요약·문서 변환·이력서 초안 생성의 기본 후보로 사용합니다. 실제 이력서 품질은 원문과 대조해 검수해야 합니다. [공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-6-luna)
*   **Gemini**: 기존 기본값은 `gemini-2.0-flash`이며, `GEMINI_MODEL`로 변경할 수 있습니다. 무료 사용 가능 여부·지원 모델·할당량은 계정에서 확인하며 무료 실행을 보장하지 않습니다.

OpenAI 경로는 **Responses API + `reasoning.effort=medium`**을 사용합니다. Luna의 Chat Completions 도구 호출은 `reasoning_effort=none`일 때만 지원되므로, 모델명만 교체하지 않고 추론과 도구 호출을 함께 사용할 수 있는 경로로 변경했습니다. `temperature`는 전송하지 않습니다. [공식 이전 안내](https://developers.openai.com/api/docs/guides/latest-model)

로컬 `.env`에서 `OPENAI_MODEL=gpt-6-luna`와 `OPENAI_API_KEY`를 설정합니다. `OPENAI_MODEL`을 생략해도 Luna를 사용합니다. 다른 모델로 변경할 때는 Responses API·도구 호출·`medium` 추론 지원을 확인하세요. 이 엔진은 API 키로 호출하며, 이 설정이 ChatGPT/Codex 로그인 세션을 재사용하는 것은 아닙니다.

개인 이력서 처리 시 Responses 객체 저장을 비활성화(`store=False`)하고, 도구 실행 이후 추론 상태는 암호화된 콘텐츠로 재전달합니다. 이것이 별도 데이터 보존 정책이나 Zero Data Retention 보장을 의미하지는 않습니다. [공식 추론 상태 안내](https://developers.openai.com/api/docs/guides/reasoning)

**검증 범위:** 과거 GPT 경로 실행 기록은 당시 `gpt-5-mini` 기준입니다. Luna 전환의 요청 형식·도구 왕복·텍스트 출력은 외부 호출 없는 회귀 테스트로 확인하며, 실제 Luna API의 계정 접근·과금·이력서 생성 품질은 별도 실호출 검증이 필요합니다.

```bash
uv run job-agent job-search     # Agent 1: 공고 탐색·분석
uv run job-agent revise  # 이력서/자소서 맞춤화
```

---

## 📂 주요 결과물
*   `result/job_search_results.md`: 통합 공고 분석 리포트
*   `result/revised/{기업명}_cover_letter.md`: 맞춤형 자기소개서
*   `result/revised/{기업명}_resume_strategy.md`: 이력서 보완 및 면접 전략 가이드
*   `result/site_resumes/{기업명}_{사이트}.json`: 사이트별 이력서 입력 패키지
*   `result/site_resumes/{기업명}_{사이트}.md`: 사람이 검수하기 쉬운 사이트별 저장 초안
*   `result/site_form_maps/*.json`: 채용 사이트 페이지에서 추출한 폼/버튼 selector 스냅샷
*   `result/site_field_mappings/*.json`: 이력서 패키지 필드와 DOM selector 후보의 연결 계획

---

## 🧪 테스트 및 프로토타이핑 (`job_agent/examples/search_probe.py`)
*   **용도**: 에이전트를 실행하기 전, Tavily 검색 엔진의 쿼리 결과가 어떻게 나오는지 원시 데이터(Raw Data)를 미리 확인하는 테스트 스크립트입니다.
*   **사용 시점**: 검색 키워드나 사이트 필터(`site:wanted.co.kr` 등)를 수정했을 때, API 비용을 절약하며 검색 품질을 검증하고 싶을 때 사용합니다.
*   **실행**: `uv run python -m job_agent.examples.search_probe`

## 회사 자체 채용사이트

고정된 5개 플랫폼 외에도 사용자가 지정한 회사 채용 URL을 등록할 수 있습니다. 회사별 설정은 코드가 아닌 ignored `result/company_targets/`에 저장하며, `SiteRegistry`가 접속 범위를, `ApplicationAdapter`가 관찰한 양식과 검수된 공통 이력서의 변환을 담당합니다. LLM 호출 없이 동작합니다.

```powershell
uv run job-agent target-register --key company-example --name "Example Company" --url "https://careers.example.com/apply"
uv run job-agent form-map --target result/company_targets/company-example.json --mode playwright --headed --interactive
uv run job-agent application-prepare --target result/company_targets/company-example.json --master result/master_resume/master_resume.json --form-map "<수집된 form-map JSON>" --output-dir result/company_applications/example
```

직접 로그인하고 실제 작성 화면에서 Enter로 수집합니다. 여러 단계/팝업은 각 화면을 따로 수집하고 서로 다른 출력 폴더를 사용합니다. 등록 URL과 같은 origin(프로토콜·호스트·포트)만 허용합니다. 다른 채용 대행 호스트/iframe이 필요하면 확인 후 등록 시 `--allow-origin "https://ats.example.com"`을 추가합니다. 로그인 비밀번호·토큰이 포함된 URL은 등록하지 마세요.

출력은 `schema.json`(문항·필수값·제한·선택지), `bindings.json`(입력칸과 공통 이력서 경로 연결), `package.json`, `mapping.json`, `review.json`입니다. 자동 연결은 휴리스틱 후보이며 승인된 입력이 아닙니다. `review.json`의 `source_fields`를 참고해 `bindings.json`의 `bindings`를 수정합니다. 예: `"field_2": ["summary", "experience"]`는 두 검수 문단을 순서대로 합칩니다. 양식이 바뀌면 digest 검사로 기존 연결을 거부합니다.

```powershell
uv run job-agent application-prepare --target result/company_targets/company-example.json --master result/master_resume/master_resume.json --form-map "<동일한 form-map JSON>" --bindings result/company_applications/example/bindings.json --output-dir result/company_applications/example
uv run job-agent form-fill --site company-example --target result/company_targets/company-example.json --package result/company_applications/example/package.json --mapping result/company_applications/example/mapping.json
```

`mapping.json`의 입력값·selector를 개별 검수해 필요한 항목만 `approved: true`로 표시합니다. 위 입력 명령은 검증만 수행합니다. 실제 입력은 `--apply` 및 `APPLY` 확인이 필요하며, 사이트 자동저장으로 전송될 수 있습니다. 최종 저장/지원은 사용자만 수행합니다.

새로운 회사 전용 자기소개 문항은 답을 지어내지 않고 `review.json`에 미작성 항목으로 남깁니다. 기존 `revise` 흐름으로 문항에 맞게 작성·원문 검수한 뒤 공통 master에 근거와 함께 추가하고 재변환합니다. 글자수 초과는 자동 절단하지 않습니다. 파일 업로드·동의 체크박스·반복 경력 추가·custom 선택 UI·캡차는 자동 처리하지 않으며 수동 작업/별도 어댑터가 필요합니다. 일반 텍스트·native select·contenteditable 입력과 iframe/open shadow 수집을 사용하는 기반은 [Playwright 공식 입력 문서](https://playwright.dev/python/docs/input)를 따릅니다. 실제 회사 채용사이트에서의 전체 흐름은 회사별 검증이 필요합니다.

## 패키지 구조

```text
resum/
  job_agent/
    core/        # LangGraph 엔진, 프로젝트 경로, 결과 저장
    agents/      # 공고 탐색, 서류 수정, 사이트 패키지 생성
    documents/   # DOCX 읽기, 문서 컨텍스트, 근거 검증/컴파일
    browser/     # 브라우저 세션, DOM 수집, 필드 연결/입력
    sites/       # 사이트 URL/별칭 및 작성 규격
    examples/    # 독립 실행 가능한 실험 코드
    cli.py       # 통합 명령 진입점
  tests/
  docs/
  knowledge/     # 기존 개인 자료, Git 제외
  more_info/     # 기존 작성 지침, Git 제외
  result/        # 기존 결과와 로그인 프로필, Git 제외
```

`ProjectPaths`가 프로젝트 기준 경로를 관리하고, `ArtifactStore`가 저장 범위를 제한합니다. `DocxReader`, `ResumeLibrary`, `UserContextLoader`는 문서 처리를 담당합니다. `BrowserSession`은 로그인 프로필과 세션 수명을 소유하고, `FormFiller`는 검수된 입력 계획의 복사본을 보관하며 실제 필드를 재검증합니다. 사이트 규격은 LLM 코드와 분리했습니다.

```powershell
uv sync --extra browser
uv run job-agent --help
uv run job-agent job-search
uv run job-agent revise
uv run job-agent site-package
uv run job-agent library extract --source "<이력서.docx>"
uv run job-agent library build --corpus result/resume_library/corpus.json --draft result/master_resume/reviewed_draft.json
uv run job-agent form-map --mode playwright --sites wanted --headed --interactive
```

`python -m job_agent <명령>`도 동일하게 지원합니다. 상대 자료/결과 경로는 현재 작업 디렉토리가 아닌 `resum/` 기준입니다. 설치된 `job-agent` 명령은 다른 디렉토리에서도 기존 자료와 로그인 프로필을 사용합니다. 개발 설치(`uv sync`)를 기준으로 하며, 휠 배포 시 자료 디렉토리 설정은 별도 구성이 필요합니다. 기존 루트 Python 파일을 직접 실행하던 명령은 통합 CLI로 변경했습니다.
