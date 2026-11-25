from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.controllers import (
    auth, chat, dashboard, exam_assignments, exams, job_profiles, matching, my_training,
    question_import, resumes, system, talent, training, vector,
)
from app.core.config import settings
from app.core.db import SessionLocal, engine, redis_healthy
from app.core.response import ApiError, error_response, ok
from app.core.security import decode_token
from app.models.orm import SysOperationLog

app = FastAPI(title=f"{settings.app_name} · MVP-1", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MODULE_OF = {
    "/api/auth": "认证",
    "/api/chat": "ChatAI",
    "/api/resumes": "简历",
    "/api/job-profiles": "岗位条件",
    "/api/positions": "岗位条件",
    "/api/matching": "匹配",
    "/api/talent-profiles": "人才画像",
    "/api/exams": "测评",
    "/api/question-banks": "测评",
    "/api/questions": "测评",
    "/api/training": "培训",
    "/api/training-courses": "培训",
    "/api/prejob-plans": "培训",
    "/api/vector": "向量",
    "/api/system": "系统",
}


@app.middleware("http")
async def audit(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    cost_ms = int((time.perf_counter() - started) * 1000)

    if request.method in WRITE_METHODS and request.url.path.startswith("/api"):
        try:
            user_id, username = None, ""
            header = request.headers.get("authorization", "")
            if header.lower().startswith("bearer "):
                payload = decode_token(header.split(" ", 1)[1].strip())
                user_id = int(payload.get("sub"))
                username = payload.get("username", "")

            module = next((v for k, v in MODULE_OF.items() if request.url.path.startswith(k)), "其他")
            action = {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}[request.method]
            with SessionLocal() as db:
                db.add(SysOperationLog(
                    user_id=user_id,
                    username=username,
                    module=module,
                    action=action,
                    method=request.method,
                    path=request.url.path[:255],
                    params=None,
                    ip=request.client.host if request.client else "",
                    status="success" if response.status_code < 400 else "failed",
                    duration_ms=cost_ms,
                ))
                db.commit()
        except Exception:
            pass  # 审计失败不影响主流程

    response.headers["X-Response-Time-ms"] = str(cost_ms)
    return response


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError):
    return error_response(exc.code, exc.message, exc.http_status)


@app.exception_handler(RequestValidationError)
async def handle_validation(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", [])[1:])
    return error_response(422, f"参数校验失败：{loc} {first.get('msg', '')}".strip(), 422)


@app.exception_handler(StarletteHTTPException)
async def handle_http(request: Request, exc: StarletteHTTPException):
    return error_response(exc.status_code, str(exc.detail), exc.status_code)


@app.get("/api/health")
def health():
    db_ok = True
    db_error = ""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_ok, db_error = False, str(exc)[:200]
    return ok({
        "status": "ok" if db_ok else "degraded",
        "mysql": db_ok,
        "mysql_error": db_error,
        "redis": redis_healthy(),
        "storage": settings.storage_backend,
        "env": settings.env,
    })


for module in (auth, resumes, job_profiles, matching, dashboard, system, talent, exams,
               exam_assignments, my_training, question_import, training, vector, chat):
    app.include_router(module.router, prefix="/api")
