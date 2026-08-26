"""FastAPI依赖：运行时、配置和演示认证。"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from app.core.auth import AuthError, decode_access_token
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
    request: Request,
    token: str | None = Header(default=None, alias="X-Demo-Token"),
    authorization: str | None = Header(default=None),
) -> str:
    # 保留 X-Demo-Token 让旧 Day14 测试和离线演示继续可用。
    if token in DEMO_TOKEN_TO_USER:
        return DEMO_TOKEN_TO_USER[token]
    if authorization and authorization.lower().startswith("bearer "):
        settings: AppSettings = request.app.state.settings
        try:
            return decode_access_token(authorization[7:].strip(), secret=settings.jwt_secret)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    raise HTTPException(status_code=401, detail="缺少或无效的认证令牌。")
