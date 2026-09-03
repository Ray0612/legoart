"""PartPlacement —— 一块板件在某一层的落位（同色大板合并的输出）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PartPlacement:
    design_id: str
    color_id: str
    layer: int
    x: int  # 左上角 stud 坐标（col）
    y: int  # 左上角 stud 坐标（row）
    w: int  # studs 宽
    h: int  # studs 深

    @property
    def area(self) -> int:
        return self.w * self.h
