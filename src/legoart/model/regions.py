"""显著性 / 凸起区域对象（D6）。"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class SaliencyMap:
    """与色格网格同尺寸的显著性分数图 (H, W) 0..1。"""

    score: np.ndarray
    threshold: float = 0.5

    def __post_init__(self) -> None:
        self.score = np.asarray(self.score, dtype=np.float64)


@dataclass(slots=True)
class Region:
    """一块凸起区域：mask 为 (H, W) bool；可来自 AI 或用户手绘。"""

    mask: np.ndarray
    raise_layers: int = 1
    source: str = "ai"  # ai | user
    score: float = 0.0
    label: str = ""

    def __post_init__(self) -> None:
        self.mask = np.asarray(self.mask, dtype=bool)

    @property
    def area(self) -> int:
        return int(self.mask.sum())

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        ys, xs = np.nonzero(self.mask)
        if len(xs) == 0:
            return (0, 0, 0, 0)
        return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


@dataclass(slots=True)
class RegionSet:
    regions: list[Region] = field(default_factory=list)
