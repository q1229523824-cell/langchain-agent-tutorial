"""轻量 JWT 认证：用于作品集演示，生产环境应接入企业 IdP/OAuth。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt


class AuthError(ValueError):
    """令牌无效、过期或主体缺失。"""


def create_access_token(*, user_id: str, secret: str, expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        "typ": "access",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, *, secret: str) -> str:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AuthError("令牌无效或已过期。") from exc
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise AuthError("令牌缺少用户身份。")
    return user_id
