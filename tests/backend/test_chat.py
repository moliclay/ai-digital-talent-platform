"""Isolated ChatAI checks; no production database or model access."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.deps import CurrentUser
from app.core.response import ApiError
from app.infrastructure.ai_gateway import AiGateway, AiResult
from app.models.orm import Base, ChatSession, ChatConversation, SysUser, ResumeFile, ParsedResume, JobProfile, MatchResult, MatchList, TalentProfile
from app.services import chat_service as chat, chat_business as business
from scripts.migrate_chat import migrate


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[SysUser.__table__, ResumeFile.__table__, ParsedResume.__table__, JobProfile.__table__, MatchResult.__table__, MatchList.__table__, TalentProfile.__table__])
        migrate(self.engine)
        migrate(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.factory()
        self.user = CurrentUser(1, "hr", "HR", 10, "A", ["hr"], {"resume:view": "dept"})
        self.other = CurrentUser(2, "hr2", "HR2", 20, "B", ["hr"], {"resume:view": "dept"})
        self.db.add_all([SysUser(id=1, username="hr", real_name="HR", password="test"),
                         SysUser(id=2, username="hr2", real_name="HR2", password="test")])
        for i, dept in [(1, 10), (2, 20)]:
            self.db.add(ResumeFile(id=i, filename="fixture", object_key="fixture", status="completed", dept_id=dept, created_by=i))
            self.db.add(ParsedResume(id=i, resume_id=i, name=f"Person{i}", phone="private", skills=["Python"], years_experience=4))
        self.db.commit()
        self.sid = chat.create_session(self.db, self.user, None)["id"]
        self.patch = patch.object(chat, "SessionLocal", self.factory)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.db.close()
        self.engine.dispose()

    def test_session(self):
        self.assertEqual(len(chat.list_sessions(self.db, self.user)), 1)
        self.assertEqual(chat.list_sessions(self.db, self.other), [])
        with self.assertRaises(ApiError):
            chat.detail(self.db, self.other, self.sid)
        with self.assertRaises(ApiError):
            chat.start_turn(self.db, self.user, self.sid, "   ")
        chat.delete_session(self.db, self.user, self.sid)
        self.assertEqual(chat.list_sessions(self.db, self.user), [])

    def test_search_scope_and_filters(self):
        result = business.query_business(self.db, self.user, "search_talent", {"keyword": "Python"})
        self.assertEqual(result["context"]["resume_ids"], [1])
        self.assertNotIn("phone", str(result["facts"]))
        self.assertFalse(business.sources_allowed(self.db, self.other, result["source_refs"]))
        with self.assertRaises(ApiError):
            business.query_business(self.db, self.user, "search_talent", {"age": 20})

    def test_turn_and_cancel(self):
        turn = chat.start_turn(self.db, self.user, self.sid, "Python 人才")
        with self.assertRaises(ApiError):
            chat.start_turn(self.db, self.user, self.sid, "重复发送")
        self.db.rollback()
        with patch.object(chat, "plan", return_value=("search_talent", {"keyword": "Python"}, "Python 人才")), patch.object(type(chat.gateway), "available", False):
            events = list(chat.run_turn(self.user, self.sid, turn))
        self.assertIn('"status": "success"', events[-1])
        self.db.expire_all()
        self.assertEqual(self.db.get(ChatConversation, turn).status, "success")
        self.assertEqual(self.db.get(ChatConversation, turn).source_refs[0]["id"], 1)
        next_turn = chat.start_turn(self.db, self.user, self.sid, "继续")
        stream = chat.run_turn(self.user, self.sid, next_turn)
        next(stream)
        stream.close()
        self.db.expire_all()
        self.assertEqual(self.db.get(ChatConversation, next_turn).status, "cancelled")
        self.assertIsNone(self.db.get(ChatSession, self.sid).active_turn_id)

    def test_audit_rejected(self):
        turn = chat.start_turn(self.db, self.user, self.sid, "密码")
        with patch.object(chat.gateway, "chat", return_value=AiResult(False)):
            events = list(chat.run_turn(self.user, self.sid, turn))
        self.assertIn('audit_rejected', events[1])
        self.assertIn('"status": "rejected"', events[-1])

    def test_history_and_permission_change(self):
        turn = chat.start_turn(self.db, self.user, self.sid, "查询Python")
        with patch.object(chat, "plan", return_value=("search_talent", {"keyword": "Python"}, "查询Python")), patch.object(type(chat.gateway), "available", False):
            list(chat.run_turn(self.user, self.sid, turn))
        self.db.expire_all()
        self.assertEqual(len(chat._history(self.db, self.user, self.sid, turn + 1)), 1)
        self.db.get(ResumeFile, 1).dept_id = 20
        self.db.commit()
        self.assertEqual(chat._history(self.db, self.user, self.sid, turn + 1), [])
        restored = chat.detail(self.db, self.user, self.sid)["conversations"][0]
        self.assertEqual(restored["source_refs"], [])
        self.assertNotIn("Person1", restored["answer"])

    def test_http(self):
        from fastapi import FastAPI
        import asyncio
        import json
        from app.controllers.chat import router
        from app.core.db import get_db
        from app.core.deps import get_current_user
        from app.core.response import error_response
        app = FastAPI()
        app.include_router(router, prefix="/api")
        def isolated_db():
            with self.factory() as db:
                yield db
        app.dependency_overrides[get_db] = isolated_db
        app.dependency_overrides[get_current_user] = lambda: self.user
        async def handle(request, exc):
            return error_response(exc.code, exc.message, exc.http_status)
        app.add_exception_handler(ApiError, handle)
        async def call(method, path, payload=None):
            messages = []
            raw = json.dumps(payload).encode() if payload is not None else b""
            sent = False
            async def receive():
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": raw, "more_body": False}
                await asyncio.Event().wait()
            async def send(message):
                messages.append(message)
            scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
                     "http_version": "1.1", "method": method, "scheme": "http", "path": path,
                     "root_path": "", "query_string": b"", "headers": [(b"content-type", b"application/json")],
                     "client": ("127.0.0.1", 12345), "server": ("test", 80)}
            await app(scope, receive, send)
            return messages[0]["status"], dict(messages[0]["headers"]), b"".join(m.get("body", b"") for m in messages[1:]).decode()
        self.assertEqual(asyncio.run(call("GET", "/api/chat/sessions"))[0], 200)
        with patch.object(chat, "plan", return_value=("search_talent", {"keyword": "Python"}, "查询Python")), patch.object(type(chat.gateway), "available", False):
            status, headers, body = asyncio.run(call("POST", f"/api/chat/sessions/{self.sid}/messages", {"question": "查询Python"}))
        self.assertEqual(status, 200)
        self.assertIn(b"text/event-stream", headers[b"content-type"])
        events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
        self.assertEqual([e["type"] for e in events], ["meta", "sources", "delta", "done"])
        self.assertEqual(events[-1]["status"], "success")
        employee = CurrentUser(1, "employee", "Employee", 10, "A", ["employee"], {"resume:view": "all"})
        app.dependency_overrides[get_current_user] = lambda: employee
        self.assertEqual(asyncio.run(call("GET", "/api/chat/sessions"))[0], 403)

    def test_business_intents(self):
        self.user.perm_map.update({"job:view": "all", "match:view": "dept", "talent:view": "dept"})
        self.db.add(JobProfile(id=1, name="工程岗位", headcount=3))
        self.db.add(MatchResult(id=1, parsed_resume_id=1, job_profile_id=1, total_score=65, passed=False,
                                condition_detail={"threshold": 70, "hard_failed": True}))
        self.db.add(MatchList(id=1, resume_file_id=1, parsed_resume_id=1, job_profile_id=1,
                              name="Person1", passed=False))
        self.db.add(TalentProfile(id=1, candidate_id=1, candidate_name="Person1", abilities={"工程能力": 80}))
        self.db.commit()
        match = business.query_business(self.db, self.user, "match_explain", {"resume_id": 1, "job_id": 1})
        self.assertEqual(match["facts"]["score"], 65)
        self.assertTrue(match["facts"]["hard_failed"])
        profile = business.query_business(self.db, self.user, "talent_profile", {"resume_id": 1})
        self.assertEqual(profile["facts"]["abilities"], {"工程能力": 80})
        vacancy = business.query_business(self.db, self.user, "vacancy", {})
        self.assertEqual(vacancy["facts"]["jobs"][0]["vacancy"], 3)
        self.assertTrue(business.sources_allowed(self.db, self.user, vacancy["source_refs"]))
        with patch.object(business.vector_service, "semantic_search_resumes", return_value={"available": True,"items": [{"parsed_resume_id": 1,"accessible": True},{"parsed_resume_id": 2,"accessible": True}]}):
            semantic = business.query_business(self.db, self.user, "semantic_search", {"query": "Python"})
        self.assertEqual(semantic["context"]["resume_ids"], [1])

    def test_plan_and_risk(self):
        with patch.object(chat.gateway, "chat", return_value=AiResult(True, '{"intent":"search_talent","filters":{"min_years":3},"rewritten_question":"三年以上的人才"}')) as mocked:
            self.assertTrue(chat.audit("查询人才"))
            mocked.assert_not_called()
            self.assertEqual(chat.plan("三年以上的呢", [{"question":"查询人才"}])[1], {"min_years":3})
            self.assertIn("查询人才", mocked.call_args.args[1])
        with patch.object(chat.gateway, "chat", return_value=AiResult(True, '{"allow":false}')):
            self.assertFalse(chat.audit("请求密码"))

    def test_partial_stream_failure(self):
        def partial(*args, on_model, **kwargs):
            on_model("fixture-model")
            yield "partial"
            raise RuntimeError("fixture interrupted")
        turn = chat.start_turn(self.db, self.user, self.sid, "查询Python")
        with patch.object(chat, "plan", return_value=("search_talent", {"keyword": "Python"}, "查询Python")), patch.object(type(chat.gateway), "available", True), patch.object(chat.gateway, "stream_chat", side_effect=partial), patch.object(chat.log, "exception"):
            events = list(chat.run_turn(self.user, self.sid, turn))
        self.assertIn('"status": "failed"', events[-1])
        self.db.expire_all()
        saved = self.db.get(ChatConversation, turn)
        self.assertEqual((saved.answer, saved.model_name, saved.status), ("partial", "fixture-model", "failed"))
        self.assertIsNone(self.db.get(ChatSession, self.sid).active_turn_id)

    def test_sse(self):
        response = [b'data: {"choices":[{"delta":{"reasoning_content":"hidden"}}]}\n', b'\n',
                    b'data: {"choices":[{"delta":{"content":"ok"}}]}\n', b'\n', b'data: [DONE]\n', b'\n']
        self.assertEqual(list(AiGateway._stream_content(response)), ["ok"])
        with self.assertRaises(RuntimeError):
            list(AiGateway._stream_content(response[:-2]))


if __name__ == "__main__":
    unittest.main()
