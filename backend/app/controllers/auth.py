from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ok
from app.core.security import decode_token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    return ok(auth_service.login(db, payload.username.strip(), payload.password))


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        try:
            jti = decode_token(authorization.split(" ", 1)[1].strip()).get("jti", "")
            auth_service.logout(jti)
        except Exception:
            pass
    return ok({"logged_out": True})


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok({
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "department_id": user.department_id,
            "department_name": user.department_name,
            "roles": user.roles,
            "data_scope": user.scope,
        },
        "menus": auth_service.visible_menus(db, user),
        "permissions": sorted(user.permissions),
    })
