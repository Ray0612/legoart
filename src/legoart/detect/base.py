"""拍照识别（D12）：图片 → 零件候选（颜色必选，形态由用户确认）。

候选 = 图片里一块"可能是单个积木"的色块：给出位置/面积/平均色/最近官方色
与 ΔE00。零件形态识别不可靠 → 由 UI 让用户下拉确认（需求方已确认此口径）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(slots=True)
class PartCandidate:
    """一个疑似积木的色块。"""

    x: int
    y: int
    w: int
    h: int
    area: int
    avg_rgb: tuple[int, int, int]  # 平均色 0..255
    palette_color_id: str          # 最近官方色（BrickLink 名）
    delta: float                   # CIEDE2000 距离
    label: str = ""

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)


class PhotoDetector(Protocol):
    """predict(np (H,W,3) uint8 RGB) -> list[PartCandidate]。"""

    kind: str

    def predict(self, rgb: np.ndarray) -> list[PartCandidate]: ...
