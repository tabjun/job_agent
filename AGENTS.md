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

- **Agent 1 (Job Search & Resume Reviser)**: `job_hunter.py`(공고 탐색·기업분석, 실행 가능), `revise_resume.py`(이력서/자소서 맞춤화)
- **Agent 2 (Master Resume Builder)**: 설계 단계, 전용 파일 아직 없음. 목표는 `knowledge/` 사실을 정규화한 `master_resume.yaml` 단일 원천 관리
- **Agent 3 (ResumeOps Sync)**: `site_resume_agent.py`, `site_form_mapper.py`, `site_form_connector.py`(사이트별 규격 변환·폼 매핑, Playwright 반자동 — 로그인·최종저장은 사용자)
- 공용 엔진: `agent.py`(`LangGraphAgentEngine`)
- LangChain/LangGraph 예제 및 실험: `langchain_agent.py`, `langgraph_agent.py`
- 기타 실험: `construction_agent.py`
- 사용자 사실 데이터: `knowledge/`, `more_info/`
- 결과물: `result/`
- **원칙: 공고 탐색·서류 생성은 AI, 최종 검토·저장·제출은 사용자(Human-in-the-loop).**

로컬 에이전트 스킬, 플러그인 캐시, 개인 설정은 `.agents/`, `.codex/`, `.claude/settings.local.json`에 둘 수 있지만 Git에 커밋하지 않는다.

## 5. 변경 원칙

- 먼저 검색하고 읽은 뒤 수정한다.
- 프롬프트, 도구, 상태 그래프, 파일 입출력 변경은 작게 나누어 수행한다.
- 기능 변경에는 가능한 최소 검증을 붙인다.
- 생성 결과나 개인정보성 파일을 커밋 후보에 올리지 않는다.
- 변경 후 필요한 내용은 `history.md`, `process.md`, `conversation_l2_cache.md` 중 맞는 곳에 갱신한다.

## 6. Codex/Claude 병행 작업 규칙

이 저장소는 Codex와 로컬 Claude를 병행해서 사용할 수 있다. 어느 에이전트가 작업하더라도 흐름이 끊기지 않도록 아래 규칙을 따른다.

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
