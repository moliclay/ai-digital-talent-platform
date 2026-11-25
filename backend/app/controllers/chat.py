from __future__ import annotations

import anyio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ok
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["ChatAI"])


class ChatStreamingResponse(StreamingResponse):
    async def stream_response(self, send):
        try:
            await super().stream_response(send)
        finally:
            with anyio.CancelScope(shield=True):
                await self.body_iterator.aclose()


class SessionInput(BaseModel):
    title: str | None = Field(default=None, max_length=128)


class MessageInput(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@router.get("/sessions")
def sessions(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return ok(chat_service.list_sessions(db, user))


@router.post("/sessions")
def create(body: SessionInput, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return ok(chat_service.create_session(db, user, body.title))


@router.get("/sessions/{session_id}")
def detail(session_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return ok(chat_service.detail(db, user, session_id))


@router.delete("/sessions/{session_id}")
def remove(session_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    chat_service.delete_session(db, user, session_id)
    return ok()


@router.post("/sessions/{session_id}/messages")
def message(session_id: int, body: MessageInput, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    turn_id = chat_service.start_turn(db, user, session_id, body.question)
    iterator = chat_service.run_turn(user, session_id, turn_id)
    sentinel = object()

    async def events():
        try:
            while True:
                chunk = await anyio.to_thread.run_sync(next, iterator, sentinel)
                if chunk is sentinel:
                    break
                yield chunk
        finally:
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(iterator.close)

    return ChatStreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
