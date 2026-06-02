from fastapi import APIRouter

from app.api.v1.endpoints.structure import structure_router

api_router = APIRouter()
api_router.include_router(structure_router)

