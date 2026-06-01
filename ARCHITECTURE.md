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
│   ├── main.py                              # FastAPI 앱, 라우터 등록, DI(어댑터 → Orchestrator) 조립
│   ├── api/
│   │   └── v1/
│   │       ├── api.py                       # v1 APIRouter 집합
│   │       └── endpoints/
│   │           └── structure.py             # [Router] 구조화 HTTP 엔드포인트
│   ├── services/
│   │   └── structuring_orchestrator.py    # [Service] 파이프라인 오케스트레이션
│   ├── schemas/
│   │   ├── request.py                       # [Schema] API 요청 DTO
│   │   ├── response.py                      # [Schema] API 응답·구조화 결과 DTO
│   │   └── errors.py                        # [Schema] API 에러 응답 DTO
│   ├── ports/
│   │   ├── llm_port.py                      # [Port] Single-shot 구조화 추론 계약
│   │   ├── prompt_port.py                   # [Port] 프롬프트 로드·버전 계약
│   │   └── formatter_port.py                # [Port] Markdown/표 렌더 계약
│   └── infrastructure/
│       ├── llm/
│       │   └── langchain_llm_adapter.py   # [Infrastructure] LangChain LLM 구현
│       ├── formatters/
│       │   └── markdown_formatter.py        # [Infrastructure] Markdown 포맷 구현
│       └── prompts/
│           └── templates/
│               └── prompt_repository.py     # [Infrastructure] 프롬프트 템플릿·버전 구현
├── config/
│   └── settings.py                          # 환경 설정 (API 키, 모델, 기본 prompt_version)
├── DESIGN.md                                # 제품·로드맵
├── ARCHITECTURE.md                          # 본 문서
└── pyproject.toml
```

---

## 3. 계층별 역할

### 3.1 Router — `app/api/v1/endpoints/`

**역할:** HTTP 경계. 요청 파싱·`StructureRequest` 검증·Orchestrator **단일 호출**·`StructureResponse` 또는 표준 에러 반환.

**규칙**

- `async def` 엔드포인트만 사용.
- 비즈니스 로직·프롬프트·LLM·포맷팅 **금지**.
- `infrastructure/` **직접 import 금지**.

---

### 3.2 Service — `app/services/structuring_orchestrator.py`

**역할:** 유스케이스 오케스트레이터. Single-shot 파이프라인 순서·예외 변환·응답 조립.

**파이프라인 (고정 순서, 전 단계 async)**

```
1. PromptPort.load(version)           → 프롬프트 확보
2. LLMPort.extract_structured(...)    → Single-shot: 3필드 raw 추출 (1회 호출)
3. Pydantic → StructuredResult        → 스키마 검증 (실패 시 도메인 예외)
4. FormatterPort.render(...)          → formatted_body 생성
5. StructureResponse + RunMeta 조립   → Router에 반환
```

**규칙**

- `ports/`·`schemas/`만 의존. `infrastructure/` **import 금지**.
- Port는 생성자(또는 `main.py` DI)로 **주입**.
- LLM 다단계 호출·필드별 분리 호출 **사용하지 않음**.

---

### 3.3 Port — `app/ports/`

**역할:** Service가 필요로 하는 **추상 계약**(Protocol 또는 ABC). Infrastructure 교체 지점.

| Port | 책임 | 메서드 방향 |
|------|------|-------------|
| `LLMPort` | 입력 텍스트 + 프롬프트로 **한 번에** 구조화 raw 반환 | `async` |
| `PromptPort` | `prompt_version`별 템플릿 로드 | `async` |
| `FormatterPort` | `StructuredResult` → Markdown/표 문자열 | `async` |

Service는 구현체(LangChain, 파일 경로 등)를 **알지 않는다**.

---

### 3.4 Infrastructure — `app/infrastructure/`

**역할:** Port **구현체(Adapter)**. LangChain, 템플릿 파일, Markdown 렌더 등 외부 기술 캡슐화.

**규칙**

- `ports/`·`schemas/`(및 필요 시 `config/`)만 import.
- `api/`, `services/` **import 금지**.
- 모든 I/O·LLM 호출 **`async`**.

---

### 3.5 Schema — `app/schemas/`

**역할:** 계층 간 **계약(DTO)**. API·Orchestrator·LLM 파싱 결과의 단일 구조 정의.

| 모듈 | 주요 타입 (개념) |
|------|------------------|
| `request.py` | `StructureRequest` — `raw_text`, `output_format`, `prompt_version` 등 |
| `response.py` | `StructuredResult`(summary, keywords, action_points), `StructureResponse`, `RunMeta` |
| `errors.py` | HTTP 매핑용 에러 바디 |

AI 응답 불일치는 Orchestrator 단계에서 Pydantic 검증으로 **조기 실패** → 안정성.  
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
| Infrastructure → Port, Schema, config | Infrastructure → Service, api |
| Router → Service, Schema | Router → Infrastructure |
| `main.py`에서 Adapter 생성 후 Orchestrator에 주입 | Orchestrator 내부에서 Adapter `new` |

### 4.3 DI 조립

- **`app/main.py`** 에서만 Infrastructure 인스턴스를 생성하고 Port 타입으로 Orchestrator에 전달한다.
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

## 7. 예외 흐름 (개념)

| 발생 위치 | Service 변환 (예) | Router HTTP (예) |
|-----------|-------------------|------------------|
| LLM 타임아웃 | `PipelineTimeoutError` | 504 |
| JSON/파싱 실패 (Single-shot 후) | `StructureParseError` | 422 |
| Pydantic 검증 실패 | `InvalidStructureError` | 422 |
| Provider 오류 | `ExternalServiceError` | 502 |

Infrastructure 예외는 Adapter에서 잡아 Service 수준 예외로 올리고, Router는 **HTTP 매핑만** 담당한다.

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
