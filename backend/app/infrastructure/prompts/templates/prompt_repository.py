import os
import aiofiles
from app.ports.prompt_port import PromptPort


class PromptRepository(PromptPort):
    async def load_prompt(self, prompt_version: int) -> str:
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, f"v{prompt_version}.txt")

        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            return await f.read()
