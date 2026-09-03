"""Core Facade —— UI（桌面/Web）唯一允许调用的高层 API（技术方案 §2 分层规则）。

M0 提供目录/调色板装配；生成链路（generate_plan）随 M1 pipeline 落地。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .catalog import Catalog
from .catalog.loader import default_catalog_dir
from .color import Palette
from .errors import NotSupportedError


@lru_cache(maxsize=4)
def load_catalog(data_dir: str | Path | None = None, *, version: str = "curated-v0") -> Catalog:
    """装载统一目录（幂等缓存）。"""
    return Catalog.from_dir(Path(data_dir) if data_dir else None, version=version)


def build_palette(catalog: Catalog | None = None) -> Palette:
    """由目录颜色构建调色板（含 recommended 掩码，nearest 时按 color_set 过滤）。"""
    cat = catalog or load_catalog()
    if not cat.colors:
        from .errors import CatalogError

        raise CatalogError("目录中没有颜色数据", code="ERR_CATALOG")
    return Palette(cat.colors)


def generate_plan(*args, **kwargs):
    """M1 起提供：端到端方案生成。"""
    raise NotSupportedError("generate_plan 将在 M1 里程碑实现")
