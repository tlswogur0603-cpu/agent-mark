from fastapi import APIRouter, Depends

from config.settings import settings
from app.container import get_orchestrator
from app.ports.formatter_port import FormatType
from app.schemas.errors import StructuringException
from app.schemas.request import StructureRequest
from app.schemas.response import StructureResponse

from app.services.structuring_orchestrator import StructuringOrchestrator


structure_router = APIRouter(prefix="/structure", tags=["Structure"])


@structure_router.post("/", response_model=StructureResponse)
async def structure(
    request: StructureRequest,
    orchestrator: StructuringOrchestrator = Depends(get_orchestrator),
) -> StructureResponse:
    try:
        format_type = FormatType(request.output_format)
    except ValueError as exc:
        raise StructuringException(
            code="VALIDATION_ERROR",
            message="지원하지 않는 output_format입니다.",
            details=str(exc),
        ) from exc

    prompt_version = (
        request.prompt_version
        if request.prompt_version is not None
        else settings.DEFAULT_PROMPT_VERSION
    )

    return await orchestrator.execute(
        text=request.raw_text,
        prompt_version=prompt_version,
        format_type=format_type,
    )
