from fastapi import APIRouter, Depends

from app.api.dependencies import get_settings
from app.core.config import AppSettings
from app.schemas.commerce import HealthResponse


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="服务健康检查")
def health(settings: AppSettings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.version,
        api_prefix=settings.api_v1_prefix,
        llm_enabled=settings.use_llm,
    )
