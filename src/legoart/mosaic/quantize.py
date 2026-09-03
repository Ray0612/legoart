"""量化：逐格 CIEDE2000 最近官方色匹配 → GridModel（技术方案 §6.1）。"""

from __future__ import annotations

import numpy as np

from ..color import Palette
from ..errors import ColorError
from ..model import GridModel


def quantize_grid(
    rgb_cells: np.ndarray,
    palette: Palette,
    *,
    color_set: str = "recommended",
) -> tuple[GridModel, np.ndarray]:
    """把 (H, W, 3) 每格代表色映射到官方色。

    Returns:
        grid: GridModel（colors 为 color_id 的 (H, W) object 数组）
        deltas: (H, W) float —— 每格 ΔE00 残差
    """
    arr = np.asarray(rgb_cells, dtype=np.float64)
    if arr.ndim != 3 or arr.shape[-1] != 3:
        raise ColorError(f"rgb_cells 须为 (H,W,3)，got {arr.shape}")
    h, w = arr.shape[:2]
    if h < 1 or w < 1:
        raise ColorError("空网格无法量化")
    flat = arr.reshape(-1, 3)
    ids, de = palette.nearest(flat, color_set=color_set)
    grid = GridModel(width=w, height=h, colors=ids.reshape(h, w))
    return grid, de.reshape(h, w)
