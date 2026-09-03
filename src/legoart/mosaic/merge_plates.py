"""同色大板合并（D5 / 技术方案 §6.4）：把一层色格矩阵切成尽量大的矩形板。

算法：行主序贪心 —— 每个未分配格作为锚点，先向右扩展同色水平 run，再向下
扩展（行内全段同色未分配）得到候选矩形；在矩形内放入面积最大的合法板型
（白名单、允许旋转，同面积优先"横放"）。单遍 O(≈H·W)，96×64 网格毫秒级。

性质：同层无重叠、无缝隙；空位（'' 格，无砖）不参与、不覆盖。
输出：该层 PartPlacement[]。
"""

from __future__ import annotations

import numpy as np

from ..catalog.models import PartSpec
from ..errors import DataError
from ..model import GridModel, PartPlacement

_EMPTY = ""  # 空位哨兵（无砖层格）


def _best_plate(by_area: list[PartSpec], rw: int, rh: int) -> tuple[PartSpec, int, int] | None:
    """在 (rw×rh) 矩形内选面积最大的板；返回 (plate, 放置宽, 放置高)。"""
    for p in by_area:
        pw, ph = p.stud_w, p.stud_h
        if rw >= pw and rh >= ph:
            return p, pw, ph
        if rw >= ph and rh >= pw:
            return p, ph, pw  # 旋转（横放优先于竖放：上面先试 as-is 主方向）
    return None


def merge_grid(grid: GridModel, plates: list[PartSpec], *, layer: int = 0) -> list[PartPlacement]:
    """把一层网格合并为 PartPlacement 列表（含旋转的板型选择）。"""
    h, w = grid.height, grid.width
    colors = grid.colors
    if not any(p.stud_area == 1 for p in plates):
        raise DataError("板型白名单缺少 1×1 板（3024 类），无法保证覆盖")
    by_area = sorted(plates, key=lambda p: -p.stud_area)

    assigned = np.zeros((h, w), dtype=bool)
    placements: list[PartPlacement] = []

    for y in range(h):
        x = 0
        while x < w:
            if assigned[y, x] or colors[y, x] == _EMPTY:
                x += 1
                continue
            cid = colors[y, x]
            # 1) 水平 run
            x2 = x
            while x2 < w and not assigned[y, x2] and colors[y, x2] == cid:
                x2 += 1
            rw = x2 - x
            # 2) 向下扩展（每行 [x, x2) 全段同色未分配）
            y2 = y
            while y2 < h:
                row = colors[y2, x:x2]
                if np.any(row != cid) or np.any(assigned[y2, x:x2]):
                    break
                y2 += 1
            rh = y2 - y
            # 3) 在矩形内放最大板（锚点 (x, y)）
            chosen = _best_plate(by_area, rw, rh)
            if chosen is None:  # 白名单放不下该剩余形状 → 留待终检报错
                x += 1
                continue
            plate, pw, ph = chosen
            assigned[y : y + ph, x : x + pw] = True
            placements.append(
                PartPlacement(
                    design_id=plate.design_id,
                    color_id=cid,
                    layer=layer,
                    x=x,
                    y=y,
                    w=pw,
                    h=ph,
                )
            )
            # 直接前进到板右缘，剩余格在后续扫描时以新的 run 处理
            x += pw

    # 校验：无重叠、覆盖面积 = 非空格数、每件单色
    cover = np.zeros((h, w), dtype=bool)
    for p in placements:
        block = cover[p.y : p.y + p.h, p.x : p.x + p.w]
        if block.any():
            raise DataError(f"合并算法出现重叠: {p}")
        block[:] = True
        if not ((colors[p.y : p.y + p.h, p.x : p.x + p.w] == p.color_id).all()):
            raise DataError(f"合并算法混色: {p}")
    expected = int((colors != _EMPTY).sum())
    if int(cover.sum()) != expected:
        raise DataError(f"合并覆盖不完整: {cover.sum()} != {expected}（板型白名单过窄？）")
    return placements


def merge_stats(placements: list[PartPlacement], cells: int) -> dict:
    """质量统计（回显给用户，技术方案 §6.4）。"""
    n = len(placements)
    total = sum(p.area for p in placements)
    ones = sum(1 for p in placements if p.area == 1)
    return {
        "parts": n,
        "avg_area": round(total / n, 2) if n else 0.0,
        "largest_area": max((p.area for p in placements), default=0),
        "pct_1x1": round(100.0 * ones / n, 1) if n else 0.0,
        "covered_cells": total,
        "cells": cells,
    }
