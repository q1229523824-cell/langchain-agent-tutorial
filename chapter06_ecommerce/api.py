"""Day14旧导入路径的兼容层；正式FastAPI应用已经迁移到 ``app.main``。"""

from app.main import app, create_app

__all__ = ["app", "create_app"]
