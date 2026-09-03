"""legoart —— 乐高画作智能转换器核心算法库。

纯 Python、零 UI 依赖。PyQt6 桌面端与未来 Web 端（FastAPI）均通过
``legoart.api`` 提供的领域 API 复用本包。

里程碑：M0 脚手架（包骨架 + 色彩核心 + 目录装载 + 存储最小库）。
"""

__version__ = "0.1.0"

from .errors import (
    CatalogError,
    ColorError,
    DataError,
    LegoArtError,
    LegoArtTimeoutError,
    NotSupportedError,
    StorageError,
    TimeoutError as _TimeoutError,  # 保留兼容（模块内真实类名）
)

__all__ = [
    "__version__",
    "LegoArtError",
    "CatalogError",
    "ColorError",
    "DataError",
    "LegoArtTimeoutError",
    "NotSupportedError",
    "StorageError",
]
