from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """API 공통 에러 응답 DTO (HTTPException 핸들러용)."""

    code: str = Field(
        ...,
        description='시스템 내부 식별용 에러 코드 (예: "VALIDATION_ERROR", "LLM_FAILURE").',
    )
    message: str = Field(
        ...,
        description="클라이언트에 전달할 사용자 친화적 에러 메시지.",
    )
    details: Optional[str] = Field(
        default=None,
        description="실험·디버깅용 상세 정보(로그, 스택 트레이스 등). 생략 가능.",
    )


class StructuringException(Exception):
    """서비스 내부에서 발생하는 도메인 예외 신호."""

    def __init__(self, code: str, message: str, details: str = None):
        # API 응답용 DTO를 미리 생성하여 품고 있습니다.
        self.error_response = ErrorResponse(
            code=code, 
            message=message, 
            details=details
        )
        super().__init__(message)