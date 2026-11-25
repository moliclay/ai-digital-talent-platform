"""Run legacy business regressions with database and vector targets isolated."""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))
from app.core.config import settings

suffix = sys.argv[1]
if not re.fullmatch('[0-9a-f]{10}', suffix):
    raise SystemExit('Expected isolated environment suffix')
base = 'http://127.0.0.1:18080'
with urllib.request.urlopen(base + '/api/health', timeout=5) as response:
    assert json.load(response)['data']['env'] == 'test'
env = dict(os.environ)
env.update(DATABASE_URL=make_url(settings.db_url).set(database='ai_talent_accept_'+suffix).render_as_string(hide_password=False), APP_ENV='test', REDIS_URL='redis://127.0.0.1:6379/14', MILVUS_RESUME_COLLECTION='accept_resumes_'+suffix, MILVUS_JOB_COLLECTION='accept_jobs_'+suffix, PYTHONUTF8='1')
allowed = {'p2_test', 's2_brief_test', 's3_identity_test', 's4_assignment_test', 's5_onboard_test', 's7_acceptance_test', 'ocr_test'}
results = {}
for name in sys.argv[2:]:
    if name not in allowed:
        raise SystemExit('Unknown suite')
    print('---', name, flush=True)
    results[name] = subprocess.run([sys.executable, '-B', str(ROOT/'tests/backend'/ (name+'.py')), base], cwd=BACKEND, env=env).returncode
print('SUITE RESULTS', results, flush=True)
raise SystemExit(int(any(results.values())))
