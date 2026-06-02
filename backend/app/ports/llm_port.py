from typing import Protocol, runtime_checkable
from app.schemas.response import StructuredResult

@runtime_checkable
class LLMPort(Protocol):
    """
    LLM 추론을 위한 추상 계약(Port).
    이 인터페이스를 구현하는 모든 클래스는 extract_structured 메서드를 가져야 함.
    """

    async def extract_structured(self, text: str, prompt: str) -> StructuredResult:
        """
        원문 텍스트와 로드된 프롬프트를 받아 구조화된 결과를 반환한다.
        """
        ...

