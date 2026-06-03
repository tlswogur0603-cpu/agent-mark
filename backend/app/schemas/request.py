from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from config.settings import settings


class StructureRequest(BaseModel):
    """구조화 API 요청 DTO (FastAPI 요청 검증용)."""

    raw_text: str = Field(
        ...,
        description="사용자가 입력하는 비정형 텍스트.",
        min_length=1,
    )
    output_format: str = Field(
        default=settings.DEFAULT_OUTPUT_FORMAT,
        description='구조화 결과의 출력 포맷 (예: "markdown", "table").',
    )
    prompt_version: Optional[int] = Field(
        default=None,
        description=(
            "프롬프트 템플릿 버전. 미입력 시 None이며, "
            "서비스 계층에서 settings.DEFAULT_PROMPT_VERSION을 적용한다."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "raw_text": (
                    "지난 분기 회의에서 신규 온보딩 플로우 도입과 "
                    "고객 지원 SLA 24시간 대응 개선이 결정되었다."
                ),
                "output_format": "markdown",
                "prompt_version": 1,
            },
        },
    )

