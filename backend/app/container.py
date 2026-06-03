from config.settings import settings
from app.infrastructure.formatters.markdown_formatter import MarkdownFormatter, MarkdownFormatterAdapter
from app.infrastructure.llm.langchain_llm_adapter import LangChainLLMAdapter
from app.infrastructure.prompts.templates.prompt_repository import PromptRepository
from app.services.structuring_orchestrator import StructuringOrchestrator
from app.ports.formatter_port import FormatterPort, FormatType
from app.schemas.response import StructuredResult


def get_orchestrator() -> StructuringOrchestrator:
    # 의존성 조립
    llm = LangChainLLMAdapter(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.DEFAULT_MODEL,
    )
    prompt_provider = PromptRepository()
    formatter = MarkdownFormatterAdapter(MarkdownFormatter())

    return StructuringOrchestrator(
        llm=llm,
        prompt_provider=prompt_provider,
        formatter=formatter,
        model_name=settings.DEFAULT_MODEL,
    )

