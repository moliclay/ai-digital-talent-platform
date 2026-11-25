"""统一返回 {code, message, data} 与业务异常。"""
from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


def page(items: list, total: int, p: int, page_size: int) -> dict:
    return {"items": items, "total": total, "page": p, "page_size": page_size}


class ApiError(Exception):
    """业务异常：由全局处理器转成统一响应，不抛裸 HTTPException。"""

    def __init__(self, code: int, message: str, http_status: int | None = None):
        self.code = code
        self.message = message
        self.http_status = http_status or (code if 400 <= code <= 599 else 400)
        super().__init__(message)


def error_response(code: int, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": None},
    )
