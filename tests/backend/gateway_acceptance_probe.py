import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from app.services import chat_service
from app.infrastructure.ai_gateway import gateway
original = gateway.chat
def inspect(*args, **kwargs):
    result = original(*args, **kwargs)
    print('ok=', result.ok, 'latency=', result.latency_ms, 'error=', result.error, 'text=', result.text[:500], flush=True)
    return result
gateway.chat = inspect
try:
    print(chat_service.plan('查找拥有 Python 技能的人才', []))
except Exception as exc:
    print(type(exc).__name__, str(exc))
