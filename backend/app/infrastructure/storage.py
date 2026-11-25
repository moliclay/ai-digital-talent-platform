"""对象存储适配器。MVP 用本地文件，接口与 MinIO 一致，换后端只改配置。

MinIO 落地时新增 MinioStorage 实现同样的三个方法即可，业务层零改动。
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import settings


class LocalStorage:
    backend = "local"

    def __init__(self, root: Path | None = None):
        self.root = Path(root or settings.storage_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, data: bytes, subdir: str = "resumes") -> tuple[str, int]:
        suffix = Path(filename).suffix.lower() or ".bin"
        today = datetime.now().strftime("%Y/%m")
        key = f"{subdir}/{today}/{uuid.uuid4().hex}{suffix}"
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key, len(data)

    def path_of(self, key: str) -> Path:
        path = (self.root / key).resolve()
        root = self.root.resolve()
        if not str(path).startswith(str(root)):
            raise ValueError("非法的对象路径")
        return path

    def url_of(self, key: str) -> str:
        # 本地模式用受保护的下行接口，前端带 token 取流
        return f"/api/resumes/file/{key}"

    def delete(self, key: str) -> None:
        path = self.path_of(key)
        if path.exists():
            path.unlink()

    def reset(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)


def get_storage() -> LocalStorage:
    if settings.storage_backend != "local":
        raise RuntimeError(
            f"STORAGE_BACKEND={settings.storage_backend} 尚未实现，MVP 仅支持 local；"
            "接入 MinIO 时新增 MinioStorage 并在此返回"
        )
    return LocalStorage()
