# 🚀 Resume & Job Hunter AI Agent (LangGraph + GPT-5-mini)

이 프로젝트는 **LangGraph**와 **GPT-5-mini / Gemini 1.5 Pro**를 활용하여 사용자의 이력서와 기업의 재무/평판 데이터를 분석하고, 최적의 채용 공고 선정부터 맞춤형 자기소개서 작성, 면접 가이드까지 제공하는 고도화된 AI 에이전트 시스템입니다.

## 🏗️ 프로젝트 구조

프로젝트는 **엔진(Engine)**과 **어플리케이션(Application)** 레이어로 분리되어 설계되었습니다.

*   **`agent.py` (Engine Layer)**: 
    *   LangGraph를 활용한 범용 에이전트 오케스트레이션 엔진입니다.
    *   상태 관리(State), 모델 호출 로직, 도구 실행(Tool Execution) 순환 구조를 캡슐화한 **슈퍼클래스/뼈대** 역할을 합니다. 
    *   Gemini와 GPT-5-mini 간의 선택적 구동을 지원합니다.
*   **`job_hunter.py` (Application Layer)**: 
    *   `agent.py` 엔진을 상속/활용하여 채용 컨설팅이라는 구체적인 업무를 수행합니다.
    *   로컬 데이터(이력서, 가이드라인)를 로드하고 채용 관련 특화 도구들을 주입합니다.

---

## ✨ 핵심 고도화 및 설계 의도

단순히 공고를 긁어오는 수준을 넘어, **"AI가 마음대로 지어내는 거짓말(Hallucination)"**을 막고 사용자의 **"실제 커리어 철학"**이 담긴 결과물을 만들도록 설계되었습니다.

### 1. 로컬 데이터 컨텍스트 연동 (`load_user_context`)
*   **의도**: 에이전트가 외부 공고 정보만 보고 답변하는 것이 아니라, 사용자의 실제 데이터(`knowledge/`, `more_info/`, `self_introduction/`)를 먼저 학습하도록 강제합니다.
*   **구조**: 폴더별로 이력서, 작성 가이드, 과거 자소서를 분리하여 관리함으로써 에이전트가 상황에 맞는 정확한 근거 데이터를 참조할 수 있습니다.

### 2. 강력한 프롬프트 엔지니어링 (Hallucination 및 뻔한 멘트 차단)
*   **의도**: JD에 맞추기 위해 사용자의 이력을 허위로 부풀리거나, "귀사의 비전에 감명받았다" 같은 영혼 없는 멘트가 생성되는 것을 방지합니다.
*   **설계**: `more_info/guideline.txt`에 적힌 사용자의 가치관(예: '데이터를 통한 정답 도출의 즐거움')을 자소서의 메인 테마로 삼도록 명령합니다. 또한, 이력서에 없는 기술이나 프로젝트 언급 시 엄격하게 차단하도록 설계되었습니다.

### 3. 멀티 스테이지 파이프라인 및 특화 도구
*   **의도**: 정보 수집과 문서 작성을 분리하여 결과물의 퀄리티를 높입니다.
*   **기능**: 
    *   `get_financial_health`: 겉보기에만 화려한 기업이 아닌, 실제 내실(재무 상태)을 보고 지원 여부를 결정할 수 있게 돕습니다.
    *   `save_cover_letter`: 분석 리포트와 실제 제출용 자소서를 분리하여, 사용자가 `result/` 폴더에서 즉시 제출 가능한 문서를 확인할 수 있게 편의성을 극대화했습니다.

---

## 🛠️ 설치 및 사용법 (Step-by-Step)

### 1. 저장소 복제 (Git Clone)
먼저 프로젝트를 로컬 환경으로 가져옵니다.
```bash
git clone <repository_url>
cd resum
```

### 2. 환경 설정 및 패키지 설치 (UV 사용)
현대적인 파이썬 패키지 관리자인 `uv`를 사용합니다.
```bash
# uv 초기화 및 가상환경 생성
uv init
uv venv

# 필수 라이브러리 설치
uv pip install langchain-openai langchain-google-genai langgraph python-dotenv aiohttp langchain-tavily
```
### 3. API 키 설정 (.env)
루트 디렉토리에 `.env` 파일을 생성하고 필요한 API 키를 입력합니다.

| API 키 명칭 | 용도 | 발급처 |
| :--- | :--- | :--- |
| `GOOGLE_AI_API_KEY` | 기본 분석 모델 (Gemini 1.5 Pro) | [Google AI Studio](https://aistudio.google.com/) |
| `OPENAI_API_KEY` | 고성능/가성비 모델 (GPT-5-mini) | [OpenAI Platform](https://platform.openai.com/) |
| `TAVILY_API_KEY` | 실시간 채용 공고 및 기업 평판 검색 | [Tavily AI](https://tavily.com/) |
| `DART_API_KEY` | 기업 재무 상태 및 공시 정보 조회 | [OpenDART](https://opendart.fss.or.kr/) |

---

## 🐳 고급 설정: 로컬 LLM 및 Docker 사용법

### 1. 로컬 LLM 연동 (Ollama 활용)
클라우드 API 대신 내 컴퓨터의 자원을 사용하고 싶다면 **Ollama**를 통해 로컬 모델을 서빙할 수 있습니다.

*   **준비**: [Ollama](https://ollama.com/) 설치 후 `ollama run llama3.1` (또는 최신 모델) 실행
*   **코드 수정 (`agent.py`)**:
    ```python
    from langchain_community.chat_models import ChatOllama

    # OpenAI 대신 로컬 모델 사용 시
    self.llm = ChatOllama(model="llama3.1", base_url="http://localhost:11434").bind_tools(self.tools)
    ```

### 2. Docker 이미지 빌드 및 실행
환경에 구애받지 않고 실행하기 위해 도커를 사용할 수 있습니다.

*   **Dockerfile 생성**:
    ```dockerfile
    FROM python:3.11-slim
    COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
    WORKDIR /app
    COPY . .
    RUN uv pip install --system -r requirements.txt
    CMD ["python", "job_hunter.py"]
    ```
*   **실행**:
    ```bash
    docker build -t job-hunter-agent .
    docker run --env-file .env job-hunter-agent
    ```

---

### 4. 사용자 데이터 준비
에이전트가 나를 알 수 있도록 데이터를 폴더에 넣어주세요. (현재는 `.txt` 파일 지원)
*   `knowledge/resume.txt`: 나의 상세 이력서
*   `more_info/guideline.txt`: 내가 지향하는 자소서 작성 방향성 및 철학
*   `self_introduction/`: 과거에 썼던 자소서 샘플들

### 5. 코드 실행
```bash
python job_hunter.py
```
실행 후 터미널의 안내에 따라 직군, 경력, 지역 조건을 입력하고 사용할 AI 모델을 선택하세요.

---

## 🤖 AI 모델 가이드 (2026.05 기준)

*   **Gemini 1.5 Pro**: 구글의 무료 티어를 활용하며 일반적인 분석에 적합합니다.
*   **GPT-5-mini**: 2026년 기준 가장 가성비가 뛰어난 모델입니다. (기존 GPT-4o 대비 10배 저렴하며, 일일 사용 한도가 55배 더 넉넉함)

---

## 📂 결과물 (Result)
분석이 완료되면 `result/` 폴더에 다음과 같은 결과물이 생성됩니다.
*   `{기업명}_cover_letter.md`: 내 철학이 담긴 맞춤형 자소서
*   `{기업명}_final_guide.md`: 재무/평판 분석 및 면접 준비 가이드
