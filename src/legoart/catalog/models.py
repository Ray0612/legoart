"""目录条目数据模型（JSON schema 与之对应，见 data/catalog/curated）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ColorSpec:
    """色库条目。

    color_id 约定：BrickLink 色名（本库主键）；name_tlg 为乐高官方命名，
    未知时可为空串（运行时回退显示 name_bl）。
    rgb 为十六进制串（如 "#C91A09"）或 "C91A09"。
    """

    color_id: str
    name_bl: str
    name_tlg: str = ""
    rgb_hex: str = "#000000"
    is_trans: bool = False
    material: str = "solid"
    recommended: bool = True
    refs: dict[str, Any] = field(default_factory=dict)

    @property
    def rgb(self) -> tuple[int, int, int]:
        h = self.rgb_hex.lstrip("#")
        if len(h) != 6:
            raise ValueError(f"非法 RGB 十六进制: {self.rgb_hex!r}")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    @classmethod
    def from_dict(cls, d: dict) -> "ColorSpec":
        return cls(
            color_id=str(d["color_id"]),
            name_bl=str(d.get("name_bl", d["color_id"])),
            name_tlg=str(d.get("name_tlg", "")),
            rgb_hex=str(d.get("rgb", d.get("rgb_hex", "#000000"))),
            is_trans=bool(d.get("is_trans", False)),
            material=str(d.get("material", "solid")),
            recommended=bool(d.get("recommended", True)),
            refs=dict(d.get("refs", {})),
        )

    def to_dict(self) -> dict:
        return {
            "color_id": self.color_id,
            "name_bl": self.name_bl,
            "name_tlg": self.name_tlg,
            "rgb": self.rgb_hex,
            "is_trans": self.is_trans,
            "material": self.material,
            "recommended": self.recommended,
            "refs": self.refs,
        }


@dataclass(frozen=True, slots=True)
class PartSpec:
    """零件目录条目（design_id 为乐高设计号主键，如 3024）。"""

    design_id: str
    name: str
    category: str = "Misc"
    stud_w: int = 1  # 顶面 studs 宽（拼搭面积基准）
    stud_h: int = 1  # 顶面 studs 深
    shape_family: str = "other"  # plate|brick|tile|slope|baseplate|other
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def stud_area(self) -> int:
        return max(self.stud_w, 1) * max(self.stud_h, 1)

    @classmethod
    def from_dict(cls, d: dict) -> "PartSpec":
        return cls(
            design_id=str(d["design_id"]),
            name=str(d["name"]),
            category=str(d.get("category", "Misc")),
            stud_w=int(d.get("stud_w", 1)),
            stud_h=int(d.get("stud_h", 1)),
            shape_family=str(d.get("shape_family", "other")),
            extra=dict(d.get("extra", {})),
        )

    def to_dict(self) -> dict:
        return {
            "design_id": self.design_id,
            "name": self.name,
            "category": self.category,
            "stud_w": self.stud_w,
            "stud_h": self.stud_h,
            "shape_family": self.shape_family,
            "extra": self.extra,
        }
