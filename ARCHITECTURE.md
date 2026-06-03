# AgentMark Backend Architecture

> **Single Source of Truth** — 이슈 단위 개발 시 본 문서와 `DESIGN.md`(제품 목표)를 함께 참고한다.  
> 폴더·파일 배치는 **변경하지 않는다**. 구현 세부는 각 모듈 docstring·테스트로 보완한다.

---

## 1. 설계 목표

| 목표 | 아키텍처 대응 |
|------|----------------|
| 비정형 텍스트 → 구조화 자동화 | Single-shot LLM + Orchestrator 파이프라인 |
| 요약·키워드·행동 포인트 일관 출력 | `StructuredResult` 스키마 + Pydantic 검증 |
| Markdown/표 가시화 | `FormatterPort` 어댑터 |
| 안정성·재현성 | Schema 계약, `prompt_version`·`RunMeta`, Port 교체 가능 |

**핵심 기술 결정 (고정)**

| 항목 | 결정 |
|------|------|
| LLM 전략 | **Single-shot** — LLM **1회** 호출로 `summary`, `keywords`, `action_points` 동시 추출 |
| 처리 방식 | 입출력·LLM·포맷터·프롬프트 로드 전부 **`async`/`await`** |

---

## 2. 폴더 구조

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
├── ARCHITECTURE.md                          # 본 문서 (설계 아키텍처)
└── pyproject.toml
```

---

## 3. 계층별 역할

### 3.1 Router — `app/api/v1/endpoints/`

**역할:** HTTP 경계. 요청 파싱·`StructureRequest` 검증·Orchestrator **단일 호출**·`StructureResponse` 또는 표준 에러 반환.

**규칙**

- `async def` 엔드포인트만 사용.
- 비즈니스 로직·프롬프트 로딩·LLM 호출·실제 포맷 변환 **금지**.
- `infrastructure/` **직접 import 금지**.
- **요청 단계 처리 (MVP 한정):** 프롬프트 버전은 실행에 필요한 최소 명세이므로 요청 단계에서 결정되는 것이 타당하다. Orchestrator가 설정 처리까지 담당하여 책임이 분산되는 것을 막기 위해, 라우터 단에서 `settings.DEFAULT_PROMPT_VERSION` 적용을 핸들링하여 전달한다.

---

### 3.2 Service — `app/services/structuring_orchestrator.py`

**역할:** 유스케이스 오케스트레이터. 구조화 파이프라인의 실행 흐름 제어 및 조율. 결과 구조(StructuredResult)를 신뢰하여 수행하고, 실패 발생 시 예외 처리를 전담한다. (LLM의 결과 스키마 준수 여부 검증은 Orchestrator의 역할이 아닌 LLMPort 구현체의 책임으로 위임한다.)

**파이프라인 (고정 순서, 전 단계 async)**

```
1. PromptPort.load(version)           → 프롬프트 템플릿 로드
2. LLMPort.extract_structured(...)    → Single-shot: 3필드 추출 및 스키마 검증 완료된 결과 반환 (1회 호출)
3. FormatterPort.render(...)          → formatted_body 생성 (마크다운 포맷팅 지시)
4. StructureResponse + RunMeta 조립   → Router에 반환
```

**규칙**

- `ports/`·`schemas/`만 의존. `infrastructure/` **import 금지**.
- Port는 생성자(또는 `container.py` DI)로 **주입**.
- LLM 다단계 호출·필드별 분리 호출 **사용하지 않음**.

---

### 3.3 Port — `app/ports/`

**역할:** Service가 필요로 하는 **추상 계약**(Protocol 또는 ABC). Infrastructure 교체 지점.

| Port | 책임 | 메서드 방향 |
|------|------|-------------|
| `LLMPort` | 입력 텍스트 + 프롬프트로 **한 번에** 구조화된 결과(`StructuredResult`) 반환 | `async` |
| `PromptPort` | `prompt_version`별 템플릿 로드 | `async` |
| `FormatterPort` | `StructuredResult` → 특정 포맷(Markdown 등) 문자열로 렌더링 | `async` |

Service는 구현체(LangChain, 파일 경로 등)를 **알지 않는다**.

---

### 3.4 Infrastructure — `app/infrastructure/`

**역할:** Port **구현체(Adapter)**. LangChain, 템플릿 파일, Markdown 렌더 등 외부 기술 캡슐화.

**규칙 및 MVP 상세**
- `ports/`·`schemas/`(및 필요 시 `config/`)만 import.
- `api/`, `services/` **import 금지**.
- 모든 I/O·LLM 호출 **`async`**.
- **인터페이스 확장성 및 방어적 설계:** `format_type`으로 테이블, JSON 등이 정의되어 있지만 MVP 단계에서는 마크다운 포맷만 지원하도록 의도되었다. 따라서 `MarkdownFormatterAdapter`가 Infrastructure 단계에서 이를 방어(마크다운 이외의 형식 요청 시 `NotImplementedError`를 발생시켜 Orchestrator에 예외 전파)하고 있다. Orchestrator는 단지 구조화와 포맷팅 지시만 담당할 뿐, 구체적인 마크다운 포맷의 유효 여부는 판단하지 않는다.

---

### 3.5 Schema — `app/schemas/`

**역할:** 계층 간 **계약(DTO)**. API·Orchestrator·LLM 파싱 결과의 단일 구조 정의.

| 모듈 | 주요 타입 (개념) |
|------|------------------|
| `request.py` | `StructureRequest` — `raw_text`, `output_format`, `prompt_version` 등 |
| `response.py` | `StructuredResult`(summary, keywords, action_points), `StructureResponse`, `RunMeta` |
| `errors.py` | HTTP 매핑용 에러 바디 및 `StructuringException` 도메인 예외 |

AI 응답 불일치는 LLM 어댑터 계층(Pydantic 기반 `with_structured_output` 및 검증)에서 **조기 실패**하게 함으로써 파이프라인의 안정성을 확보한다.  
`RunMeta`(prompt_version, model 등)로 실험·재현성 추적.

---

## 4. 의존성 규칙

### 4.1 두 가지 “방향”

```
[런타임 호출]     Router  →  Service  →  Infrastructure(어댑터)
[컴파일 의존]     Router  →  Service  →  Port  ←  Infrastructure(구현)
                              ↘  Schema  ↗
```

- **호출 주도권:** 위에서 아래로만 호출한다.
- **코드 의존:** 상위는 하위 **구현**이 아니라 Port·Schema에만 의존한다 (**DIP**).

### 4.2 DIP — Port와 Infrastructure

```
┌─────────────────────────────────────────┐
│  Service (Orchestrator)                 │
│    uses: LLMPort, PromptPort,           │
│          FormatterPort, Schemas         │
└─────────────────┬───────────────────────┘
                  │ depends on (abstract)
┌─────────────────▼───────────────────────┐
│  Port (Protocol / ABC)                  │
└─────────────────▲───────────────────────┘
                  │ implements
┌─────────────────┴───────────────────────┐
│  Infrastructure (Adapters)              │
│    LangChainLLMAdapter, PromptRepository, │
│    MarkdownFormatter, …                 │
└─────────────────────────────────────────┘
```

| 허용 | 금지 |
|------|------|
| Service → Port, Schema | Service → Infrastructure |
| Infrastructure → Port, Schema | Infrastructure → Service, api, config (설정 직접 참조 금지, DI 주입 사용) |
| Router → Service, Schema | Router → Infrastructure |
| `container.py`에서 Adapter 생성 후 Orchestrator에 주입 | Orchestrator 내부에서 Adapter `new` |

### 4.3 DI 조립

- **`app/container.py`** 에서만 Infrastructure 인스턴스를 생성하고 Port 타입으로 Orchestrator에 전달한다.
- 테스트 시 Port **Fake/Stub** 주입으로 Single-shot·검증 로직을 LLM 없이 검증한다.

---

## 5. Single-shot LLM 계약

**원칙:** `LLMPort.extract_structured` 한 번의 호출이 아래 3필드를 포함한 구조화 결과를 반환하도록 프롬프트·파싱을 설계한다.

| 필드 | 설명 |
|------|------|
| `summary` | 핵심 요약 |
| `keywords` | 키워드 목록 |
| `action_points` | 행동 포인트 목록 |

- Orchestrator는 **필드별 LLM 호출을 추가하지 않는다**.
- 파싱 실패·검증 실패 시 정책(재시도 1회 등)은 Orchestrator에 두되, 호출 횟수 정책의 기본값은 **1회**이다.

---

## 6. 비동기 규칙

| 계층 | 규칙 |
|------|------|
| Router | `async def` 핸들러, Orchestrator `await` |
| Service | Public 메서드 `async def`, Port 호출 전부 `await` |
| Port | 계약 메서드 `async def` |
| Infrastructure | LangChain 등 비동기 API 사용; 동기 API는 `asyncio.to_thread` 등으로 감싸지 않는 한 **비동기 클라이언트 우선** |

동기 블로킹 호출을 이벤트 루프에 섞지 않는다.

---

## 7. 예외 흐름

시스템 내부 오류는 도메인 예외인 `StructuringException`으로 통일하여 관리한다. 이 예외는 에러 발생 원인에 따라 서로 다른 HTTP 상태 코드로 매핑되어, 클라이언트가 오류 원인을 명확하게 식별할 수 있도록 돕는다. 예외 처리는 `main.py`의 글로벌 예외 핸들러에서 일괄 매핑한다.

| 예외 종류 | 발생 원인 / 위치 | 도메인 에러 코드 | HTTP 상태 코드 |
|-----------|------------------|------------------|----------------|
| 입력값 검증 실패 | 지원하지 않는 출력 포맷 요청 (Router) | `VALIDATION_ERROR` | 400 Bad Request |
| 프롬프트 로드 실패 | 파일 부재 등 템플릿 로딩 오류 (PromptRepository) | `PROMPT_LOAD_FAILURE` | 500 Internal Server Error |
| LLM 추론 오류 | API 연결 실패 또는 응답 스키마 불일치 (LLMAdapter) | `LLM_INFERENCE_FAILURE` | 502 Bad Gateway |
| 미지원 포맷 오류 | MVP 단계에서 지원하지 않는 포맷 요청 (FormatterAdapter) | `UNSUPPORTED_FORMAT` | 501 Not Implemented |
| 포맷팅 실패 | 마크다운 포맷팅 과정 중 오류 (MarkdownFormatter) | `FORMATTING_FAILURE` | 500 Internal Server Error |

- **예외 전파:** 어댑터 등 인프라 계층의 예외는 Orchestrator에서 잡아 적절한 `StructuringException`으로 래핑하여 상위로 전파한다.
- **글로벌 핸들링:** FastAPI의 Exception Handler(`main.py`)가 `StructuringException`을 감지하여 정의된 상태 코드와 에러 응답 객체(`ErrorResponse`)를 반환한다.

---

## 8. 개발 시 체크리스트

- [ ] 새 외부 연동 → `ports/` 계약 추가 → `infrastructure/` 구현 → `main.py` DI
- [ ] Orchestrator에 LLM **추가 호출** 넣지 않았는가 (Single-shot 유지)
- [ ] 추가한 I/O가 모두 `async`인가
- [ ] Service·Router가 `infrastructure`를 import하지 않았는가
- [ ] 입출력·LLM 결과 필드가 `schemas/`에 반영되었는가

---

## 9. 관련 문서

- **`DESIGN.md`** — 제품 목표, 핵심 기능, 기술 스택 선정 이유
- **`README.md`** — 실행·환경 설정
