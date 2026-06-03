import os
import aiofiles
from app.ports.prompt_port import PromptPort
from app.schemas.errors import StructuringException


class PromptRepository(PromptPort):
    async def load_prompt(self, prompt_version: int) -> str:
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, f"v{prompt_version}.txt")

        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            content = await f.read()

            if not content.strip():
                raise StructuringException(
                    code="PROMPT_LOAD_FAILURE", 
                    message=f"프롬프트 내용이 비어있습니다: v{prompt_version}.txt"
                )
                
            return content
