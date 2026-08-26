from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str


ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "认证失败"},
    404: {"model": ErrorResponse, "description": "资源不存在或无权访问"},
    422: {"model": ErrorResponse, "description": "参数校验失败"},
    429: {"model": ErrorResponse, "description": "请求过于频繁"},
    500: {"model": ErrorResponse, "description": "内部错误"},
}
