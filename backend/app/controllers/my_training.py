"""员工自助路由：我的培训（需求⑤）。

员工的账号由 HR「转正」时创建，登录后只有培训成长一个菜单。
这三条接口按 `user.id → parsed_resumes.employee_user_id` 反查自己的计划与台账，
员工不需要（也无法）传 candidate_id。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ok
from app.services import my_training_service

router = APIRouter(prefix="/my/training", tags=["我的培训"])


@router.get("/summary")
def summary(db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_perm("train", "view"))):
    """我的培训概览：计划数、任务进度、待办、台账条数。未转正返回 onboarded=false。"""
    return ok(my_training_service.summary(db, user))


@router.get("/plans")
def plans(db: Session = Depends(get_db),
          user: CurrentUser = Depends(require_perm("train", "view"))):
    """我的培养计划（含任务明细）。"""
    return ok(my_training_service.plans(db, user))


@router.get("/ledger")
def ledger(db: Session = Depends(get_db),
           user: CurrentUser = Depends(require_perm("train", "view"))):
    """我的成长台账。"""
    return ok(my_training_service.ledger(db, user))
