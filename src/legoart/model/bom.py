"""BOM：BomItem / BomModel —— 零件汇总（支持层维度的单层用量/总用量）。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class BomItem:
    design_id: str
    color_id: str
    qty: int
    layer: int | None = None  # None = 跨层合计行；具体行 = 单层用量

    @property
    def key(self) -> tuple[str, str]:
        return (self.design_id, self.color_id)


@dataclass(slots=True)
class BomModel:
    items: list[BomItem] = field(default_factory=list)

    def add(self, design_id: str, color_id: str, qty: int, layer: int | None = None) -> None:
        self.items.append(BomItem(design_id, color_id, qty, layer))

    def total_qty(self, design_id: str, color_id: str) -> int:
        return sum(i.qty for i in self.items if i.design_id == design_id and i.color_id == color_id)

    def per_layer(self, design_id: str, color_id: str) -> dict[int, int]:
        out: dict[int, int] = defaultdict(int)
        for i in self.items:
            if i.design_id == design_id and i.color_id == color_id and i.layer is not None:
                out[i.layer] += i.qty
        return dict(out)

    def totals(self) -> list[BomItem]:
        agg: dict[tuple[str, str], int] = defaultdict(int)
        for i in self.items:
            agg[i.key] += i.qty
        return [BomItem(k[0], k[1], v, layer=None) for k, v in sorted(agg.items())]

    def unique_keys(self) -> list[tuple[str, str]]:
        return sorted({i.key for i in self.items})
