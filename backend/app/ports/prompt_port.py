from typing import Protocol, runtime_checkable

@runtime_checkable
class PromptPort(Protocol):
    """프롬프트 관리 및 버저닝을 위한 추상 계약(Port)."""

    async def load_prompt(self, prompt_version: int) -> str:
        """
        특정 버전의 프롬프트 템플릿 문자열을 불러온다.
        """
        ...
