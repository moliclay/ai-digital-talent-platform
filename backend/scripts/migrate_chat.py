"""Incremental migration for ChatAI tables."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.db import engine
from app.models.orm import Base, ChatSession, ChatConversation


def migrate(bind=engine):
    Base.metadata.create_all(bind=bind, tables=[ChatSession.__table__, ChatConversation.__table__])


if __name__ == "__main__":
    migrate()
    print("ChatAI tables ready")
