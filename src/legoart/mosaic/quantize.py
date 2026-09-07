"""量化：逐格 CIEDE2000 最近官方色匹配 → GridModel（技术方案 §6.1）。

两条路径：
- ``quantize_grid``：对 (H,W,3) 平均色矩阵直接最近色（快速、测试用）；
- ``quantize_mode``：每格拆 k×k 子格、各自匹配官方色后**多数投票**——
  黑线与底色不会平均出"脏灰"再被硬配第三种色，细线/边界更干净（pipeline 默认）。
"""

from __future__ import annotations

from collections import Counter

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


def quantize_mode(
    image,
    width: int,
    height: int,
    palette: Palette,
    *,
    color_set: str = "recommended",
    k: int = 3,
) -> tuple[GridModel, np.ndarray]:
    """子格多数投票量化：源图 → (H,W) 每格颜色。

    每格被拆成 k×k 子采样点（BOX 平均），子点各自匹配最近官方色，再对该
    k×k 子点做多数投票得出格色 —— 细黑线（若占格子内多数子点）能保留，
    线与底色交界不再平均成第三种"脏灰"。
    """
    from PIL import Image

    rgb = image.convert("RGB")
    small = np.asarray(
        rgb.resize((width * k, height * k), Image.Resampling.BOX), dtype=np.float64
    )  # (H*k, W*k, 3)
    hk, wk = small.shape[:2]
    if hk < 1 or wk < 1:
        raise ColorError("空网格无法量化")
    ids, _ = palette.nearest(small.reshape(-1, 3), color_set=color_set)
    ids_img = ids.reshape(hk, wk)

    grid = GridModel.empty(width, height)
    for y in range(height):
        for x in range(width):
            block = ids_img[y * k : (y + 1) * k, x * k : (x + 1) * k]
            grid.colors[y, x] = Counter(block.ravel().tolist()).most_common(1)[0][0]

    # 残差（警告用，近似 E76）：每格平均色 vs 最终官方色
    from ..color.convert import rgb_to_lab

    mean_cells = np.asarray(
        rgb.resize((width, height), Image.Resampling.BOX), dtype=np.float64
    )  # (H,W,3)
    idx_map = {cid: i for i, cid in enumerate(palette.ids)}
    row_idx = np.array([idx_map.get(cid, 0) for cid in grid.colors.ravel()], dtype=np.int64)
    q_lab = rgb_to_lab(mean_cells.reshape(-1, 3))
    sub_lab = palette.lab[row_idx]
    de = np.sqrt(((q_lab - sub_lab) ** 2).sum(axis=1))
    return grid, de.reshape(height, width)
