from pydantic import BaseModel, ConfigDict, Field


class StructuredResult(BaseModel):
    """Single-shot LLM으로 추출한 구조화 필드."""

    summary: str = Field(..., description="입력 텍스트의 핵심 요약.")
    keywords: list[str] = Field(..., description="주제 분류·검색용 키워드 목록.")
    action_points: list[str] = Field(..., description="실행 가능한 행동 포인트 목록.")


class RunMeta(BaseModel):
    """결과 생성 환경 추적용 메타데이터 (재현성·실험 비교)."""

    prompt_version: int = Field(..., description="적용된 프롬프트 템플릿 버전.")
    model_name: str = Field(..., description="구조화 추론에 사용된 LLM 모델 식별자.")
    execution_time: int = Field(
        ...,
        ge=0,
        description="파이프라인 실행 시간(밀리초).",
    )
    timestamp: int = Field(
        ...,
        description="결과 생성 시각(Unix epoch, 초 단위).",
    )


class StructureResponse(BaseModel):
    """구조화 API 최종 응답 DTO."""

    result: StructuredResult = Field(..., description="추출·검증된 구조화 데이터.")
    formatted_body: str = Field(
        ...,
        description="FormatterPort가 생성한 Markdown 또는 표 형식 문자열.",
    )
    meta: RunMeta = Field(..., description="실행 환경 및 성능 메타데이터.")

