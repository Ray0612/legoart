"""Core Facade —— UI（桌面/Web）唯一允许调用的高层 API（技术方案 §2 分层规则）。

M0：目录/调色板装配；M1：端到端方案生成（generate_plan）。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .catalog import Catalog
from .catalog.loader import default_catalog_dir
from .color import Palette
from .model import ImageSpec, MosaicPlan


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


def generate_plan(
    image,
    spec: ImageSpec,
    *,
    progress=None,
    catalog: Catalog | None = None,
    palette: Palette | None = None,
) -> MosaicPlan:
    """端到端生成方案。默认使用内置目录/调色板；可注入覆盖（测试/服务端）。"""
    from . import pipeline

    cat = catalog or load_catalog()
    pal = palette or build_palette(cat)
    return pipeline.generate_plan(image, spec, palette=pal, catalog=cat, progress=progress)
