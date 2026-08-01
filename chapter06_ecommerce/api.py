"""Day 14 电商 Agent 的 FastAPI 接口。

认证仅用于作品演示：客户端提交 demo token，服务端映射为 user_id。生产环境应替换为
JWT/OAuth/session，并从认证上下文注入用户身份，不能直接信任请求体中的 user_id。
"""

from __future__ import annotations

from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from chapter06_ecommerce.observability import RateLimitExceeded
from chapter06_ecommerce.workflow import EcommerceAgentRuntime


DEFAULT_DATA_DIRECTORY = Path(__file__).resolve().parents[1] / ".agent_data" / "day14"
DEMO_TOKEN_TO_USER = {
    "demo-user-token": "demo-user",
    "other-user-token": "other-user",
}


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    request_id: str
    thread_id: str
    intent: str
    route: str
    answer: str
    citations: list[str]
    business_result: dict[str, object]
    duration_ms: float


class HealthResponse(BaseModel):
    status: str
    service: str
    llm_required_for_default_mode: bool


def create_app(
    runtime: EcommerceAgentRuntime | None = None,
    *,
    data_directory: Path = DEFAULT_DATA_DIRECTORY,
    use_llm: bool = False,
) -> FastAPI:
    runtime = runtime or EcommerceAgentRuntime.create(
        data_directory=data_directory,
        use_llm=use_llm,
    )
    app = FastAPI(
        title="星河商城电商客服 Agent",
        version="14.0.0",
        description="LangGraph 路由、混合检索、持久化记忆和安全退款的作品集 API。",
    )
    app.state.runtime = runtime

    def authenticated_user(
        token: str | None = Header(default=None, alias="X-Demo-Token"),
    ) -> str:
        if token is None or token not in DEMO_TOKEN_TO_USER:
            raise HTTPException(status_code=401, detail="缺少或无效的演示认证令牌。")
        return DEMO_TOKEN_TO_USER[token]

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_, error: RateLimitExceeded):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=429, content={"detail": str(error)})

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="day14-ecommerce-agent",
            llm_required_for_default_mode=False,
        )

    @app.post("/v1/chat", response_model=ChatResponse, tags=["agent"])
    def chat(
        request: ChatRequest,
        user_id: str = Depends(authenticated_user),
    ) -> ChatResponse:
        result = runtime.chat(
            user_id=user_id,
            thread_id=request.thread_id,
            message=request.message,
        )
        return ChatResponse.model_validate(result)

    @app.get("/v1/orders", tags=["orders"])
    def list_orders(user_id: str = Depends(authenticated_user)):
        return runtime.list_orders(user_id=user_id)

    @app.post("/v1/refunds/{confirmation_id}/confirm", tags=["refunds"])
    def confirm_refund(
        confirmation_id: str,
        user_id: str = Depends(authenticated_user),
    ):
        # 高风险写操作是独立确定性接口，不进入自然语言 Agent 路由。
        return runtime.confirm_refund(
            user_id=user_id,
            confirmation_id=confirmation_id,
        )

    @app.get("/v1/refunds/{refund_id}", tags=["refunds"])
    def refund_status(
        refund_id: str,
        user_id: str = Depends(authenticated_user),
    ):
        return runtime.refund_status(user_id=user_id, refund_id=refund_id)

    @app.get("/v1/metrics", tags=["observability"])
    def metrics(user_id: str = Depends(authenticated_user)):
        # user_id 用于要求认证；聚合指标本身不暴露原始消息。
        del user_id
        return runtime.trace_store.metrics()

    @app.get("/v1/traces", tags=["observability"])
    def traces(
        limit: int = Query(default=20, ge=1, le=100),
        user_id: str = Depends(authenticated_user),
    ):
        del user_id
        return {"traces": runtime.trace_store.recent(limit)}

    return app


app = create_app()
