"""统一HTTP错误格式和异常处理。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from chapter06_ecommerce.observability import RateLimitExceeded

from app.core.middleware import get_request_id


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    body: dict[str, object] = {
        "error": {"code": code, "message": message, "details": details},
        "request_id": request_id,
    }
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        headers={"X-Request-ID": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, error: HTTPException):
        detail = error.detail
        message = detail if isinstance(detail, str) else "请求处理失败。"
        code = {
            401: "authentication_failed",
            403: "permission_denied",
            404: "resource_not_found",
            409: "business_conflict",
        }.get(error.status_code, "http_error")
        return error_response(
            request,
            status_code=error.status_code,
            code=code,
            message=message,
            details=None if isinstance(detail, str) else detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, error: RequestValidationError):
        return error_response(
            request,
            status_code=422,
            code="validation_error",
            message="请求参数校验失败。",
            details=error.errors(),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(request: Request, error: RateLimitExceeded):
        return error_response(
            request,
            status_code=429,
            code="rate_limit_exceeded",
            message=str(error),
        )

    @app.exception_handler(ValueError)
    async def value_exception_handler(request: Request, error: ValueError):
        return error_response(
            request,
            status_code=400,
            code="invalid_argument",
            message=str(error),
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, error: Exception):
        # 不把堆栈、数据库路径或外部服务细节返回给客户端。
        del error
        return error_response(
            request,
            status_code=500,
            code="internal_error",
            message="服务暂时无法处理该请求。",
        )


def require_business_success(
    result: dict[str, object],
    *,
    not_found_message: str,
) -> dict[str, object]:
    if result.get("ok"):
        return result
    status = str(result.get("status", ""))
    if status in {"not_found", "not_found_or_not_pending"}:
        raise HTTPException(status_code=404, detail=not_found_message)
    raise HTTPException(
        status_code=409,
        detail=str(result.get("message") or result.get("reason") or "业务状态冲突。"),
    )
