"""分层结构：Layer / LayerStack（自下而上的物理层，D6/D9）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .grid import GridModel


@dataclass(slots=True)
class Layer:
    level: int  # 0 = 底板/首层，越大越靠上
    grid: GridModel


@dataclass(slots=True)
class LayerStack:
    width: int
    height: int
    layers: list[Layer] = field(default_factory=list)

    @property
    def height_total(self) -> int:
        return max((ly.level for ly in self.layers), default=0) + 1

    def add(self, level: int, grid: GridModel) -> None:
        if grid.width != self.width or grid.height != self.height:
            raise ValueError("层网格尺寸必须与 LayerStack 一致")
        self.layers.append(Layer(level=level, grid=grid))

    def level_grid(self, level: int) -> GridModel | None:
        for ly in self.layers:
            if ly.level == level:
                return ly.grid
        return None
