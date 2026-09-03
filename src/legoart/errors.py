"""统一错误体系：UI 通过错误码映射本地化文案（见 docs 技术方案 §11）。"""

from __future__ import annotations


class LegoArtError(Exception):
    """所有 legoart 错误的基类。

    Attributes:
        code: 稳定的机器可读错误码（如 ``ERR_COLOR_NO_MATCH``），
            核心包不携带人类文案，由 UI 层按 code + lang 本地化。
    """

    code = "ERR_UNKNOWN"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        self.code = code or self.code
        super().__init__(f"[{self.code}] {message}" if message else self.code)


class DataError(LegoArtError):
    """输入数据/文件问题（图片不可读、尺寸非法等）。"""

    code = "ERR_DATA"


class CatalogError(DataError):
    """零件/颜色目录数据缺失、损坏或版本不匹配。"""

    code = "ERR_CATALOG"


class ColorError(LegoArtError):
    """颜色计算问题（色空间转换、无匹配色等）。"""

    code = "ERR_COLOR"


class StorageError(LegoArtError):
    """本地存储（SQLite / 文件）读写失败。"""

    code = "ERR_STORAGE"


class TimeoutError(LegoArtError):
    """算法超过耗时预算被中断（对应需求：本地 60s 上限提示）。"""

    code = "ERR_TIMEOUT"


class NotSupportedError(LegoArtError):
    """尚未实现/明确排除的功能（如纹理保留、云端）。"""

    code = "ERR_NOT_SUPPORTED"


# 别名：从 errors 模块也可直接导入（避免与 builtins.TimeoutError 混淆的写法）
LegoArtTimeoutError = TimeoutError


# ---- 通用错误码常量（i18n 键与之一一对应）----
ERR_COLOR_NO_MATCH = "ERR_COLOR_NO_MATCH"
ERR_OVER_60S = "ERR_OVER_60S"
ERR_MODEL_MISSING = "ERR_MODEL_MISSING"
ERR_CATALOG_NOT_FOUND = "ERR_CATALOG_NOT_FOUND"
