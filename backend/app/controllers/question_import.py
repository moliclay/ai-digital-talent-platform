"""题库文件导入路由（需求⑥）：文件 → 草稿 → 人工确认落库。

两段式：
- `POST /question-banks/{id}/import` 返回草稿（**不落库**）
- `POST /question-banks/{id}/import/confirm` 提交（可改过的）草稿，批量落库
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ApiError, ok
from app.services import question_import_service

router = APIRouter(prefix="/question-banks", tags=["题库导入"])

MAX_BYTES = 10 * 1024 * 1024   # 10MB


@router.post("/{bank_id}/import")
async def import_file(bank_id: int, file: UploadFile = File(...),
                      db: Session = Depends(get_db),
                      user: CurrentUser = Depends(require_perm("exam", "create"))):
    """上传题库文件，返回题目草稿（AI 优先、规则补空）。不落库。"""
    data = await file.read()
    if not data:
        raise ApiError(400, "文件为空")
    if len(data) > MAX_BYTES:
        raise ApiError(400, f"文件超过 {MAX_BYTES // (1024 * 1024)}MB")
    return ok(question_import_service.draft(db, bank_id, file.filename or "unknown.txt", data))


@router.post("/{bank_id}/import/confirm")
def import_confirm(bank_id: int, payload: dict, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(require_perm("exam", "create"))):
    """确认导入：提交（前端可改过的）草稿数组，批量落库。同题干自动跳过。"""
    items = payload.get("questions") if isinstance(payload, dict) else None
    if items is None:
        items = payload.get("draft")
    return ok(question_import_service.confirm(db, bank_id, items or []))
