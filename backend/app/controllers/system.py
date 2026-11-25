from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ok, page
from app.services import system_service

router = APIRouter(prefix="/system", tags=["系统"])


@router.get("/users")
def users(
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("sys", "view")),
):
    items, total = system_service.list_users(db, page_no, page_size)
    return ok(page(items, total, page_no, page_size))


@router.get("/roles")
def roles(db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("sys", "view"))):
    return ok(system_service.list_roles(db))


@router.get("/operation-logs")
def logs(
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("sys", "view")),
):
    items, total = system_service.list_operation_logs(db, page_no, page_size)
    return ok(page(items, total, page_no, page_size))
