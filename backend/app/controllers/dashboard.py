from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ok, page
from app.services import dashboard_service

router = APIRouter(tags=["工作台"])


@router.get("/dashboard/overview")
def overview(db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("dashboard", "view"))):
    return ok(dashboard_service.overview(db, user))
