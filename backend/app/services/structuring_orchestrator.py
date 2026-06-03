import time

from app.ports.formatter_port import FormatterPort, FormatType
from app.ports.llm_port import LLMPort
from app.ports.prompt_port import PromptPort
from app.schemas.errors import StructuringException
from app.schemas.response import RunMeta, StructureResponse


class StructuringOrchestrator:
    """구조화 파이프라인 오케스트레이터 (비즈니스 조율·예외 변환)."""

    def __init__(
        self,
        llm: LLMPort,
        prompt_provider: PromptPort,
        formatter: FormatterPort,
        model_name: str,
    ) -> None:
        self._llm = llm
        self._prompt_provider = prompt_provider
        self._formatter = formatter
        self._model_name = model_name

    async def execute(
        self,
        text: str,
        prompt_version: int,
        format_type: FormatType,
    ) -> StructureResponse:
        started_at = time.perf_counter()

        try:
            prompt = await self._prompt_provider.load_prompt(prompt_version)
        except Exception as exc:
            self._raise_wrapped(
                "PROMPT_LOAD_FAILURE",
                "프롬프트를 불러오는 중 오류가 발생했습니다.",
                exc,
            )

        try:
            result = await self._llm.extract_structured(text, prompt)
        except Exception as exc:
            self._raise_wrapped(
                "LLM_INFERENCE_FAILURE",
                "텍스트 구조화 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                exc,
            )

        try:
            formatted_body = await self._formatter.render(result, format_type)
        except NotImplementedError as exc:
            self._raise_wrapped(
                "UNSUPPORTED_FORMAT",
                str(exc),
                exc,
            )

        except Exception as exc:
            self._raise_wrapped(
                "FORMATTING_FAILURE",
                "결과를 요청한 형식으로 변환하는 중 오류가 발생했습니다.",
                exc,
            )

        execution_time_ms = int((time.perf_counter() - started_at) * 1000)

        return StructureResponse(
            result=result,
            formatted_body=formatted_body,
            meta=RunMeta(
                prompt_version=prompt_version,
                model_name=self._model_name,
                execution_time=execution_time_ms,
                timestamp=int(time.time()),
            ),
        )

    @staticmethod
    def _raise_wrapped(code: str, message: str, exc: Exception) -> None:
        if isinstance(exc, StructuringException):
            raise exc
        raise StructuringException(
            code=code,
            message=message,
            details=str(exc),
        ) from exc
