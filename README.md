# AgentMark Backend

비정형 텍스트를 입력받아 AI(LLM)를 통해 핵심 요약, 주요 키워드, 실행 가능한 행동 포인트를 구조화된 형태로 자동 추출하고, 이를 마크다운 형식으로 제공하는 API 서버입니다.

---

## 1. 프로젝트 개요 및 목표

비정형 텍스트 데이터를 정해진 스키마 양식으로 일관성 있게 구조화하여 가시성을 높이고 데이터 활용을 용이하게 만듭니다.
* **텍스트 구조화 자동화**: 1회 LLM 호출(Single-shot)로 텍스트 내에서 요약, 키워드, 행동 포인트를 동시 추출합니다.
* **안정성 및 재현성**: LLM 응답 결과의 일관성 문제를 Pydantic 스키마 검증을 통해 차단하여 안정적인 API 응답을 보장하며, 실행 환경 메타데이터(`RunMeta`)를 기록하여 실험 재현 및 비교를 지원합니다.

---

## 2. 기술 스택 및 선정 근거

* **FastAPI (Python)**: 비동기(Async) 처리 지원을 통해 AI API 응답을 대기하는 동안 서버 자원의 효율성과 동시 처리 성능을 극대화합니다.
* **Pydantic**: 입출력 데이터 유효성 검증과 더불어 AI 응답 형식을 강제하여, 비정형 답변으로 인해 발생할 수 있는 런타임 에러를 사전에 방지합니다.
* **LangChain**: 복잡한 LLM 파이프라인 설계를 추상화하고 프롬프트 템플릿 관리의 유지보수성을 높이기 위해 도입했습니다.
* **Google Gemini (`gemini-2.5-flash`)**: 새로운 모델을 설정하느라 시간을 낭비하기보다, **기존에 발급받은 API 키(무료 티어)를 적극 활용하여 빠르게 개발 생산성을 극대화하기 위한 현실적인 선택**을 하였습니다.
* **Poetry**: 프로젝트마다 사용하는 라이브러리 버전이 충돌하지 않도록 격리된 가상환경을 제공받기 위해 사용했습니다. 특정 도구가 우월해서라기보다 **가상환경이 주는 의존성 격리라는 본질적인 이점**을 확보하기 위함입니다.

---

## 3. 아키텍처 디자인 (Port & Adapter)

본 시스템은 **DIP(의존성 역전 원칙)를 따르는 Port & Adapter 구조**를 취하고 있습니다.

### 도입 이유
* **구조적 복잡도 완화**: 외부 라이브러리(LangChain, OpenAI 등)나 인프라(파일 시스템 등)의 세부 구현이 비즈니스 로직에 침투하지 않도록 경계를 명확히 구분합니다.
* **책임 분리 및 유지보수성**: 각 모듈이 서로의 내부 구현을 알 필요 없이 추상 계약(Port)에만 의존하게 만듦으로써, 향후 LLM 모델을 교체하거나 파일 보관소를 교체하더라도 서비스 핵심 코드를 수정하지 않아도 되는 높은 확장성을 갖췄습니다.

### 구조도
```
[Client / API Request]
       │
       ▼
 ┌───────────┐      ┌─────────────────────────┐
 │  Router   ├─────►│  Service (Orchestrator) │
 └───────────┘      └────────────┬────────────┘
                                 │
                   ┌─────────────┼─────────────┐
                   ▼             ▼             ▼
              ┌─────────┐   ┌─────────┐   ┌──────────┐
              │ LLMPort │   │Prompt   │   │Formatter │
              │ (Port)  │   │  Port   │   │  Port    │
              └────▲────┘   └───▲─────┘   └────▲─────┘
                   │            │              │ (implements)
          ┌────────┴────────┐ ┌─┴─────────┐ ┌──┴───────┐
          │LangChain        │ │Prompt     │ │Markdown  │
          │  LLMAdapter     │ │ Repository│ │Formatter │
          │ (Infrastructure)│ │   (Infra) │ │ Adapter  │
          └─────────────────┘ └───────────┘ └──────────┘
```

---

## 4. 디렉토리 구조

```
backend/
├── app/
│   ├── main.py                              # FastAPI 앱 설정, 라우터 등록 및 글로벌 예외 핸들링
│   ├── container.py                         # 의존성 조립 (어댑터 생성 및 Orchestrator 주입)
│   ├── api/
│   │   └── v1/
│   │       ├── api.py                       # v1 APIRouter 집합
│   │       └── endpoints/
│   │           └── structure.py             # [Router] 구조화 HTTP 엔드포인트
│   ├── services/
│   │   └── structuring_orchestrator.py    # [Service] 파이프라인 오케스트레이션 (흐름 제어)
│   ├── schemas/
│   │   ├── request.py                       # [Schema] API 요청 DTO
│   │   ├── response.py                      # [Schema] API 응답·구조화 결과 DTO
│   │   └── errors.py                        # [Schema] API 에러 응답 DTO 및 도메인 예외 정의
│   ├── ports/
│   │   ├── llm_port.py                      # [Port] Single-shot 구조화 추론 계약
│   │   ├── prompt_port.py                   # [Port] 프롬프트 로드·버전 계약
│   │   └── formatter_port.py                # [Port] 포맷 렌더 계약
│   └── infrastructure/
│       ├── llm/
│       │   └── langchain_llm_adapter.py   # [Infrastructure] LangChain LLM 구현 및 스키마 검증
│       ├── formatters/
│       │   └── markdown_formatter.py        # [Infrastructure] Markdown 포맷터 및 어댑터 구현
│       └── prompts/
│           └── templates/
│               └── prompt_repository.py     # [Infrastructure] 프롬프트 템플릿 파일 로더
├── config/
│   └── settings.py                          # 환경 설정 (API 키, 모델, 기본 prompt_version)
├── DESIGN.md                                # 제품·로드맵
├── ARCHITECTURE.md                          # 아키텍처 가이드라인 (Single Source of Truth)
└── pyproject.toml
```

---

## 5. 시작 가이드 (Quick Start)

### 1) 환경 변수 설정
프로젝트 루트 경로에 `.env` 파일을 생성하고 아래와 같이 필요한 키값을 설정합니다.
```env
GEMINI_API_KEY=your_gemini_api_key_here
DEFAULT_MODEL=gemini-2.5-flash
```

### 2) 의존성 설치
Poetry를 사용하여 가상환경을 활성화하고 의존성 라이브러리를 빌드합니다.
```bash
# 가상환경 격리 및 의존성 설치
poetry install
```

### 3) API 서버 실행
서버는 비동기 ASGI 서버인 uvicorn을 기반으로 실행합니다.
```bash
# Uvicorn 서버 백엔드 구동 (reload 옵션으로 개발 환경 실시간 반영 가능)
poetry run uvicorn app.main:app --reload --port 8000
```

### 4) API 호출 테스트 (cURL)
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/structure/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "raw_text": "신규 온보딩 프로세스를 개선하기 위해 다음 주 월요일까지 매뉴얼 초안을 작성하기로 결정했습니다. 또한 개발팀과 프론트엔드 연동 일정을 조율할 예정입니다.",
  "output_format": "markdown",
  "prompt_version": 1
}'
```

---

## 6. 예외 규약

서버 내부에서 발생하는 오류는 `StructuringException` 도메인 에러로 래핑되어 일관된 `ErrorResponse` 바디 형태로 응답을 보장합니다.

| 에러 유형 | 도메인 코드 | HTTP 상태 코드 | 주요 원인 |
| :--- | :--- | :--- | :--- |
| **입력 유효성 실패** | `VALIDATION_ERROR` | 400 | 잘못되거나 지원하지 않는 출력 형식 요청 시 |
| **템플릿 로딩 실패** | `PROMPT_LOAD_FAILURE` | 500 | 요청한 프롬프트 파일(예: `v1.txt`)이 존재하지 않는 경우 |
| **LLM 추론 실패** | `LLM_INFERENCE_FAILURE` | 502 | LLM API 통신 장애 또는 반환 스키마 불일치 |
| **포맷 미지원** | `UNSUPPORTED_FORMAT` | 501 | MVP 단계에서 마크다운 이외의 포맷(예: table)을 요청 시 |
| **포맷팅 실패** | `FORMATTING_FAILURE` | 500 | 변환 과정 중 시스템 런타임 에러 발생 시 |
