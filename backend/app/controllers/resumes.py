from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ApiError, ok, page
from app.services import resume_service

router = APIRouter(prefix="/resumes", tags=["简历"])


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(...),
    job_profile_id: int | None = Form(default=None),
    project_demand_id: int | None = Form(default=None),
    project_name: str = Form(default=""),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("resume", "create")),
):
    payload: list[tuple[str, bytes, str]] = []
    for f in files:
        data = await f.read()
        if len(data) > 10 * 1024 * 1024:
            raise ApiError(400, f"{f.filename} 超过 10MB 上限")
        payload.append((f.filename or "resume", data, f.content_type or ""))
    return ok(resume_service.upload(db, user, payload, job_profile_id, project_demand_id, project_name))


@router.get("/queue")
def queue(db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("resume", "view"))):
    return ok(resume_service.queue_status(db, user))


@router.post("/parse-next")
def parse_next(db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_perm("resume", "create"))):
    task_id = resume_service.claim_next(db, user)
    if task_id is None:
        return ok({"task_id": None, "status": "idle", "message": "队列中没有待解析任务"})
    return ok(resume_service.process_task(db, task_id))


@router.get("")
def list_resumes(
    keyword: str = Query(default=""),
    education: str = Query(default=""),
    include_superseded: bool = Query(default=False, description="是否包含已被新版本替代的旧简历"),
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("resume", "view")),
):
    items, total = resume_service.list_resumes(db, user, keyword, education, page_no, page_size,
                                               include_superseded)
    return ok(page(items, total, page_no, page_size))


@router.post("/identity/reconcile")
def reconcile_identity_all(db: Session = Depends(get_db),
                           user: CurrentUser = Depends(require_perm("resume", "edit"))):
    """全量重算身份键（迁移后跑一次；幂等）。"""
    from app.services import identity_service
    return ok(identity_service.reconcile_all(db))


@router.get("/identity/suspected")
def suspected(db: Session = Depends(get_db),
              user: CurrentUser = Depends(require_perm("resume", "view"))):
    """疑似重复组（同名+同学历+同专业但手机号/邮箱不同）——只报不合并。"""
    from app.services import identity_service
    groups = identity_service.suspected_duplicates(db)
    return ok({"groups": groups, "total": len(groups)})


@router.get("/file/{key:path}")
def download(key: str, db: Session = Depends(get_db),
             user: CurrentUser = Depends(require_perm("resume", "view"))):
    path, filename = resume_service.open_file(db, user, key)
    return FileResponse(path, filename=filename)


@router.get("/{resume_id:int}")
def detail(resume_id: int, db: Session = Depends(get_db),
           user: CurrentUser = Depends(require_perm("resume", "view"))):
    return ok(resume_service.get_resume(db, user, resume_id))


@router.post("/{resume_id:int}/onboard")
def onboard(resume_id: int, payload: dict | None = None, db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_perm("resume", "edit"))):
    """候选人转正式员工：用手机号建账号 + 绑 employee 角色 + 授培训权限。

    初始密码只在本次响应里返回一次。
    """
    from app.services import onboard_service
    return ok(onboard_service.onboard(db, user, resume_id, payload or {}))


@router.patch("/{resume_id:int}")
def patch(resume_id: int, payload: dict, db: Session = Depends(get_db),
          user: CurrentUser = Depends(require_perm("resume", "edit"))):
    return ok(resume_service.patch_resume(db, user, resume_id, payload))


@router.delete("/queue/{task_id:int}")
def delete_task(task_id: int, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_perm("resume", "delete"))):
    resume_service.delete_task(db, user, task_id)
    return ok({"deleted": task_id})
