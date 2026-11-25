"""Seed extra fixtures only into a named isolated acceptance database."""
import os
import re
import subprocess
import sys
from pathlib import Path
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.config import settings

name = sys.argv[1]
if not re.fullmatch(r'ai_talent_accept_[0-9a-f]{10}', name):
    raise SystemExit('Expected an isolated acceptance database name')
env = dict(os.environ)
env['DATABASE_URL'] = make_url(settings.db_url).set(database=name).render_as_string(hide_password=False)
subprocess.run([sys.executable, str(ROOT / 'backend/scripts/seed_demo_extra.py')], env=env, check=True)
