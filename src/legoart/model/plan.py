"""MosaicPlan —— 端到端结果（单一数据源，驱动预览/Excel/PDF/扣减）。

支持 ``to_dict`` JSON 快照（project_history 回放），网格以嵌套列表存。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .bom import BomItem, BomModel
from .grid import GridModel
from .image_spec import ImageSpec
from .layers import Layer, LayerStack
from .placements import PartPlacement
from .regions import Region, RegionSet


@dataclass(slots=True)
class SolverResult:
    """需求轴求解结果（理想/库存三策略统一结构，技术方案 §7）。"""

    placements: list[PartPlacement] = field(default_factory=list)  # 可拼部分
    missing: list[BomItem] = field(default_factory=list)           # 缺件（策略 B）
    substituted: list[tuple[BomItem, str]] = field(default_factory=list)  # (原需求, 替代件)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.placements or self.missing or self.substituted)


@dataclass(slots=True)
class MosaicPlan:
    spec: ImageSpec
    grid: GridModel
    regions: RegionSet = field(default_factory=RegionSet)
    stack: LayerStack | None = None
    placements: list[PartPlacement] = field(default_factory=list)
    bom: BomModel = field(default_factory=BomModel)
    warnings: list[str] = field(default_factory=list)
    elapsed_ms: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "spec": self.spec.to_dict(),
            "grid": {"w": self.grid.width, "h": self.grid.height, "colors": self.grid.ids_2d()},
            "regions": [
                {
                    "mask": r.mask.tolist(),
                    "raise_layers": r.raise_layers,
                    "source": r.source,
                    "score": r.score,
                    "label": r.label,
                }
                for r in self.regions.regions
            ],
            "stack": (
                [
                    {"level": ly.level, "colors": ly.grid.ids_2d()}
                    for ly in sorted(self.stack.layers, key=lambda x: x.level)
                ]
                if self.stack
                else None
            ),
            "placements": [
                {
                    "design_id": p.design_id,
                    "color_id": p.color_id,
                    "layer": p.layer,
                    "x": p.x,
                    "y": p.y,
                    "w": p.w,
                    "h": p.h,
                }
                for p in self.placements
            ],
            "bom": [
                {"design_id": i.design_id, "color_id": i.color_id, "qty": i.qty, "layer": i.layer}
                for i in self.bom.items
            ],
            "warnings": self.warnings,
            "elapsed_ms": self.elapsed_ms,
            "generated_at": self.generated_at,
        }

    def grid_layer(self, level: int) -> GridModel | None:
        return self.stack.level_grid(level) if self.stack else None
