"""6 视角正交投影（D9 / 技术方案 §10.2）。

约定坐标：cell(col=x∈[0,W), row=y∈[0,H))，物理层 level=z∈[0, L)。
返回的视角图均为 color_id 字符串的二维表（'' = 空）。

- 顶视 top(level k)：第 k 层图案（即"拼到第 k 层"时俯视看到的最上层 = 该层新增面）；
- 仰视 bottom：level 0 底面图案（水平镜像）；
- 侧视 front/back：沿 y 轴看——每个 (x, z) 显示**最近一行**在该 (x,z) 处有砖的颜色
  （前方柱子遮挡其后的同高度砖，符合正交遮挡直觉）；
- 侧视 left/right：沿 x 轴看（同理）。
"""

from __future__ import annotations

import numpy as np

from ..model import GridModel, LayerStack

_EMPTY = ""


def _occupancy(stack: LayerStack, max_level: int) -> np.ndarray:
    """occ[level][x][y] -> color(str 或 '')，只含 level<=max_level 的砖。"""
    L = max_level + 1
    W, H = stack.width, stack.height
    occ = np.full((L, W, H), _EMPTY, dtype=object)
    for ly in stack.layers:
        if 0 <= ly.level <= max_level:
            occ[ly.level] = ly.grid.colors.T  # (W,H)
    return occ


def top_grid(stack: LayerStack, level: int) -> GridModel:
    """拼到 level 时的俯视：level 层图案（高层格在 level 之下时以空代替）。"""
    if stack.level_grid(level) is None:
        return GridModel.empty(stack.width, stack.height)
    return stack.level_grid(level)  # type: ignore[return-value]


def bottom_grid(stack: LayerStack) -> list[list[str]]:
    """仰视：level 0 底图案水平镜像。"""
    g = stack.level_grid(0)
    if g is None:
        return [[""] * stack.width for _ in range(stack.height)]
    arr = g.colors[:, ::-1]
    return [list(row) for row in arr.tolist()]


def _side(occ: np.ndarray, ax: str) -> list[list[str]]:
    """侧视投影。occ shape (L,W,H)。"""
    L, W, H = occ.shape
    if ax == "front":  # 视线沿 +y：逐 (x,z) 找最近(最小) y
        out = np.full((W, L), _EMPTY, dtype=object)
        for x in range(W):
            for z in range(L):
                for y in range(H):
                    if occ[z, x, y] != _EMPTY:
                        out[x, z] = occ[z, x, y]
                        break
        return [list(row) for row in out.tolist()]
    if ax == "back":
        out = np.full((W, L), _EMPTY, dtype=object)
        for x in range(W):
            for z in range(L):
                for y in range(H - 1, -1, -1):
                    if occ[z, x, y] != _EMPTY:
                        out[x, z] = occ[z, x, y]
                        break
        return [list(row) for row in out.tolist()]
    if ax == "left":  # 视线沿 +x：逐 (y,z) 找最小 x
        out = np.full((H, L), _EMPTY, dtype=object)
        for y in range(H):
            for z in range(L):
                for x in range(W):
                    if occ[z, x, y] != _EMPTY:
                        out[y, z] = occ[z, x, y]
                        break
        return [list(row) for row in out.tolist()]
    if ax == "right":
        out = np.full((H, L), _EMPTY, dtype=object)
        for y in range(H):
            for z in range(L):
                for x in range(W - 1, -1, -1):
                    if occ[z, x, y] != _EMPTY:
                        out[y, z] = occ[z, x, y]
                        break
        return [list(row) for row in out.tolist()]
    raise ValueError(ax)


def side_grid(stack: LayerStack, level: int, ax: str) -> list[list[str]]:
    """拼到 level 时的侧视（front/back/left/right），返回 (L 行 × W' 列) 便于竖向显示。"""
    raw = _side(_occupancy(stack, level), ax)
    # 转置：绘图层把"沿向维度"作为水平轴，层高作为垂直轴
    return [list(col) for col in zip(*raw)]


def overview_grid(stack: LayerStack) -> list[list[str]]:
    """成品俯视（封面用）：每格显示其最高一层颜色。"""
    W, H = stack.width, stack.height
    out = np.full((H, W), _EMPTY, dtype=object)
    levels = sorted(stack.layers, key=lambda x: x.level)
    for ly in levels:
        arr = ly.grid.colors
        mask = arr != _EMPTY
        out[mask] = arr[mask]
    return [list(row) for row in out.tolist()]
