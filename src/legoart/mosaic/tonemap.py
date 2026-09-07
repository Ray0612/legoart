"""自动色调适配（feedback-driven）：整体太暗则提亮、太亮则压暗。

做法：在 Lab 中按中位亮度做"增益+平移"亮度重映射，亮度相对关系保持不变
（色调一致），用网格搜索选择使"格色到官方色平均距离最小"的参数。

纯色/低方差图跳过（避免把单色图整体改色）。
"""

from __future__ import annotations

import numpy as np

from ..color import Palette
from ..color.convert import lab_to_rgb, rgb_to_lab

_RANGES = {
    # strength: (gains, offsets)
    1: (tuple(np.arange(0.82, 1.21, 0.06)), tuple(range(-4, 9, 2))),        # 温和
    2: (tuple(np.arange(0.62, 1.41, 0.06)), tuple(range(-16, 17, 2))),      # 标准
    3: (tuple(np.arange(0.5, 1.51, 0.05)), tuple(range(-20, 23, 2))),       # 强烈
}


def auto_tone(
    cells: np.ndarray,
    palette: Palette,
    *,
    strength: int = 2,
    max_cells: int = 4000,
    skip_std: float = 4.0,
) -> np.ndarray:
    """cells (H,W,3) RGB 0..255 → 亮度重映射后的 RGB；无需调整时原样返回。

    strength: 1 温和 / 2 标准 / 3 强烈 —— 决定亮度"增益+平移"的搜索范围。
    """
    arr = np.asarray(cells, dtype=np.float64)
    h, w = arr.shape[:2]
    if h < 2 or w < 2:
        return arr
    lab = rgb_to_lab(arr)
    l_std = float(lab[..., 0].std())
    if l_std < skip_std:  # 近纯色/无明暗层次：不自动调色
        return arr

    gains, offsets = _RANGES.get(int(strength), _RANGES[2])

    flat = lab.reshape(-1, 3)
    rng = np.random.default_rng(0)
    n = min(len(flat), max_cells)
    if n < len(flat):
        idx = rng.choice(len(flat), n, replace=False)
        sample = flat[idx]
    else:
        sample = flat

    l_s = sample[..., 0]
    lm = float(np.median(l_s))
    a_s = sample[..., 1:2]
    b_s = sample[..., 2:3]
    pa = palette.lab[:, 1][None, :]
    pb = palette.lab[:, 2][None, :]
    A = (a_s - pa) ** 2 + (b_s - pb) ** 2  # (S, N) 与亮度无关的部分

    best: tuple[float, float, float] | None = None
    for g in gains:
        for s in offsets:
            l2 = np.clip((l_s - lm) * g + lm + s, 2.0, 98.0)
            dl = (l2[:, None] - palette.lab[None, :, 0]) ** 2
            mean_dist = float(np.sqrt(dl + A).min(axis=1).mean())
            if best is None or mean_dist < best[0]:
                best = (mean_dist, float(g), float(s))
    _, g, s = best  # type: ignore[misc]

    L = lab[..., 0]
    L2 = np.clip((L - lm) * g + lm + s, 2.0, 98.0)
    out = lab.copy()
    out[..., 0] = L2
    return lab_to_rgb(out)
