from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import authenticated_user
from app.core.auth import create_access_token
from app.core.config import AppSettings
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.schemas.common import ERROR_RESPONSES


router = APIRouter(prefix="/auth", tags=["auth"])

# 仅用于本地演示；生产环境必须替换为密码哈希 + 用户表，不能保存明文密码。
DEMO_CREDENTIALS = {"demo-user": "demo-password", "other-user": "other-password"}


def _settings(request: Request) -> AppSettings:
    return request.app.state.settings


@router.post("/login", response_model=TokenResponse, responses=ERROR_RESPONSES, summary="获取JWT访问令牌")
def login(payload: LoginRequest, request: Request) -> TokenResponse:
    if DEMO_CREDENTIALS.get(payload.user_id) != payload.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误。")
    settings = _settings(request)
    return TokenResponse(
        access_token=create_access_token(
            user_id=payload.user_id,
            secret=settings.jwt_secret,
            expires_minutes=settings.jwt_expire_minutes,
        ),
        expires_in=settings.jwt_expire_minutes * 60,
        user_id=payload.user_id,
    )


@router.get("/me", response_model=CurrentUserResponse, responses=ERROR_RESPONSES, summary="查看当前用户")
def current_user(user_id: str = Depends(authenticated_user)) -> CurrentUserResponse:
    return CurrentUserResponse(user_id=user_id)
