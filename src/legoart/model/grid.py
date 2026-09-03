"""GridModel —— W×H 色格矩阵（格=1 stud）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class GridModel:
    """色格矩阵。colors 为 (H, W) 的 object 数组，元素为色库 color_id 字符串。

    说明：颜色一律以字符串 key（BrickLink 色名主键）引用，RGB 由 Palette 解析，
    避免在网格层拷贝 RGB 数值（技术方案 §5 约定）。
    """

    width: int
    height: int
    colors: np.ndarray  # dtype=object, shape (height, width)

    def __post_init__(self) -> None:
        if self.colors.shape != (self.height, self.width):
            raise ValueError(
                f"colors shape {self.colors.shape} != grid ({self.height}, {self.width})"
            )
        if self.colors.dtype != object:
            self.colors = self.colors.astype(object)

    @classmethod
    def empty(cls, width: int, height: int, fill: str = "") -> "GridModel":
        return cls(width=width, height=height, colors=np.full((height, width), fill, dtype=object))

    def ids_2d(self) -> list[list[str]]:
        return [list(row) for row in self.colors.tolist()]
