from typing import Protocol, runtime_checkable
from enum import Enum
from app.schemas.response import StructuredResult

class FormatType(Enum):
    MARKDOWN = "markdown"
    TABLE = "table"
    JSON = "json"

@runtime_checkable
class FormatterPort(Protocol):
    """구조화 결과를 특정 포맷으로 변환하는 추상 계약(Port)."""

    async def render(self, result: StructuredResult, format_type: FormatType) -> str:
        """
        StructuredResult를 받아 요청된 format_type에 맞는 문자열을 반환한다.
        """
        ...
