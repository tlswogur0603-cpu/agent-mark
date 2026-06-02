from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.schemas.errors import StructuringException, ErrorResponse

app = FastAPI(title="AgentMark API", version="0.1.0")


@app.exception_handler(StructuringException)
async def structuring_exception_handler(request: Request, exc: StructuringException):

    return JSONResponse(
        status_code=400,
        content=exc.error_response.model_dump()
    )


app.include_router(api_router, prefix="/api/v1")