"""FastAPI依赖：运行时、配置和演示认证。"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from app.core.config import AppSettings
from app.services.runtime import EcommerceAgentRuntime


DEMO_TOKEN_TO_USER = {
    "demo-user-token": "demo-user",
    "other-user-token": "other-user",
}


def get_runtime(request: Request) -> EcommerceAgentRuntime:
    return request.app.state.runtime


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def authenticated_user(
    token: str | None = Header(default=None, alias="X-Demo-Token"),
) -> str:
    if token is None or token not in DEMO_TOKEN_TO_USER:
        raise HTTPException(status_code=401, detail="缺少或无效的演示认证令牌。")
    return DEMO_TOKEN_TO_USER[token]
