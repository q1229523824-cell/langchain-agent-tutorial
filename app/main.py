"""星河商城正式FastAPI应用工厂。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.legacy import router as legacy_router
from app.core.config import AppSettings
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestIdMiddleware
from app.services.runtime import EcommerceAgentRuntime


def create_app(
    runtime: EcommerceAgentRuntime | None = None,
    *,
    settings: AppSettings | None = None,
    data_directory: Path | None = None,
    use_llm: bool | None = None,
) -> FastAPI:
    """创建可测试、可注入依赖的应用。

    ``data_directory`` 和 ``use_llm`` 保留给旧Day14入口兼容；新代码优先传入
    ``AppSettings``。
    """

    selected = settings or AppSettings.from_environment()
    if data_directory is not None or use_llm is not None:
        selected = AppSettings(
            service_name=selected.service_name,
            version=selected.version,
            api_v1_prefix=selected.api_v1_prefix,
            legacy_prefix=selected.legacy_prefix,
            data_directory=data_directory or selected.data_directory,
            use_llm=selected.use_llm if use_llm is None else use_llm,
            rate_limit=selected.rate_limit,
            cors_origins=selected.cors_origins,
        )

    runtime = runtime or EcommerceAgentRuntime.create(
        data_directory=selected.data_directory,
        use_llm=selected.use_llm,
        rate_limit=selected.rate_limit,
    )
    application = FastAPI(
        title="星河商城电商客服 Agent API",
        version=selected.version,
        description=(
            "商品推荐、政策RAG、订单查询和安全退款后端。正式接口位于 /api/v1；"
            "旧 /v1 路径仅用于兼容学习阶段。"
        ),
        contact={"name": "Agent Portfolio"},
    )
    application.state.runtime = runtime
    application.state.settings = selected
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(selected.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Demo-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    # 后添加的中间件位于外层，使CORS预检响应也能获得request_id。
    application.add_middleware(RequestIdMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router, prefix=selected.api_v1_prefix)
    application.include_router(legacy_router, prefix=selected.legacy_prefix)

    @application.get("/health", include_in_schema=False)
    def legacy_health():
        return {
            "status": "ok",
            "service": selected.service_name,
            "version": selected.version,
            "api_prefix": selected.api_v1_prefix,
            "llm_enabled": selected.use_llm,
            "llm_required_for_default_mode": False,
        }

    return application


app = create_app()
