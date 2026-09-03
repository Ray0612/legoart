"""Catalog —— 统一目录访问接口。

数据源优先级（技术方案 §9.3）：
1. ``LEGOART_DATA_DIR`` 环境变量（若设置）；
2. 仓库内 ``data/catalog/curated``（开发/随包分发用）；
3. 找不到抛 CatalogError（i18n key: ERR_CATALOG_NOT_FOUND）。

全量 Rebrickable 导入（D15）后续在本模块以相同 Catalog 接口合并。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..errors import CatalogError
from .models import ColorSpec, PartSpec


def _repo_data_dir() -> Path:
    """从代码位置向上定位仓库 data/（src/legoart/catalog/loader.py -> parents[3]）。"""
    here = Path(__file__).resolve()
    return here.parents[3] / "data" / "catalog" / "curated"


def default_catalog_dir() -> Path:
    import os

    env = os.environ.get("LEGOART_DATA_DIR")
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    p = _repo_data_dir()
    if p.is_dir():
        return p
    raise CatalogError(
        f"目录数据不存在（{p}）。可设置 LEGOART_DATA_DIR 指向 data/catalog/curated。",
        code="ERR_CATALOG_NOT_FOUND",
    )


def _load_json(path: Path, what: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise CatalogError(f"缺少目录文件: {path.name}", code="ERR_CATALOG_NOT_FOUND")
    except json.JSONDecodeError as e:
        raise CatalogError(f"{what} JSON 损坏 ({path.name}): {e}", code="ERR_CATALOG")
    if not isinstance(data, list):
        raise CatalogError(f"{what} 应为 JSON 数组 ({path.name})", code="ERR_CATALOG")
    return data


def load_colors(path: Path) -> list[ColorSpec]:
    specs = []
    seen: set[str] = set()
    for d in _load_json(path, "colors"):
        s = ColorSpec.from_dict(d)
        if s.color_id in seen:
            raise CatalogError(f"重复颜色 color_id: {s.color_id}", code="ERR_CATALOG")
        seen.add(s.color_id)
        specs.append(s)
    return specs


def load_parts(path: Path) -> list[PartSpec]:
    specs = []
    seen: set[str] = set()
    for d in _load_json(path, "parts"):
        s = PartSpec.from_dict(d)
        if s.design_id in seen:
            raise CatalogError(f"重复零件 design_id: {s.design_id}", code="ERR_CATALOG")
        seen.add(s.design_id)
        specs.append(s)
    return specs


@dataclass(slots=True)
class Catalog:
    """合并多来源的统一目录。"""

    colors: list[ColorSpec] = field(default_factory=list)
    parts: list[PartSpec] = field(default_factory=list)
    version: str = "curated-v0"
    source: str = ""
    _colors: dict[str, ColorSpec] = field(init=False, repr=False, default_factory=dict)
    _parts: dict[str, PartSpec] = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._colors = {c.color_id: c for c in self.colors}
        self._parts = {p.design_id: p for p in self.parts}

    # ---- 颜色 ----
    def color(self, color_id: str) -> ColorSpec | None:
        return self._colors.get(color_id)

    def color_ids(self, *, only_recommended: bool = False) -> list[str]:
        if not only_recommended:
            return list(self._colors)
        return [c.color_id for c in self.colors if c.recommended]

    def has_color(self, color_id: str) -> bool:
        return color_id in self._colors

    # ---- 零件 ----
    def part(self, design_id: str) -> PartSpec | None:
        return self._parts.get(design_id)

    def has_part(self, design_id: str) -> bool:
        return design_id in self._parts

    def search_parts(
        self,
        query: str = "",
        *,
        category: str | None = None,
        family: str | None = None,
        limit: int = 50,
    ) -> list[PartSpec]:
        """按 design_id / 名称模糊搜索，支持 category / shape_family 过滤。"""
        q = query.strip().lower()
        out: list[PartSpec] = []
        for p in self.parts:
            if category is not None and p.category != category:
                continue
            if family is not None and p.shape_family != family:
                continue
            if q and q not in p.design_id.lower() and q not in p.name.lower():
                continue
            out.append(p)
            if limit and len(out) >= limit:
                break
        return out

    def plate_candidates(self) -> list[PartSpec]:
        """方案可用的矩形板（按 studs 面积升序）。"""
        return sorted(
            (p for p in self.parts if p.shape_family == "plate"),
            key=lambda p: (p.stud_area, p.stud_w, p.stud_h),
        )

    @classmethod
    def from_dir(cls, data_dir: Path | None = None, *, version: str = "curated-v0") -> "Catalog":
        d = data_dir or default_catalog_dir()
        colors = load_colors(d / "colors.json")
        parts = []
        for name in ("parts_plates.json", "parts_common.json"):
            fp = d / name
            if fp.exists():
                parts.extend(load_parts(fp))
        return cls(colors=colors, parts=parts, version=version, source=str(d))
