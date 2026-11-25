"""Launch a dedicated acceptance backend with synthetic seed data."""
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from uuid import uuid4
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))
from app.core.config import settings

suffix = sys.argv[1] if len(sys.argv) > 1 else uuid4().hex[:10]
if len(suffix) != 10 or any(c not in "0123456789abcdef" for c in suffix):
    raise SystemExit("Expected a ten-character isolated environment suffix")
name = 'ai_talent_accept_' + suffix
url = make_url(settings.db_url)
env = dict(os.environ)
env.update(DATABASE_URL=url.set(database=name).render_as_string(hide_password=False),
           REDIS_URL='redis://127.0.0.1:6379/14',
           STORAGE_DIR=tempfile.mkdtemp(prefix='talent_accept_'),
           MILVUS_RESUME_COLLECTION='accept_resumes_' + suffix,
           MILVUS_JOB_COLLECTION='accept_jobs_' + suffix,
           JWT_SECRET=uuid4().hex + uuid4().hex, APP_ENV='test', PYTHONUTF8='1')
print('Acceptance DB:', name, 'vector suffix:', suffix, flush=True)
if len(sys.argv) == 1:
    subprocess.run([sys.executable, str(BACKEND / 'scripts' / 'init_db.py')], cwd=BACKEND, env=env, check=True)
subprocess.run([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18080'], cwd=BACKEND, env=env, check=True)
