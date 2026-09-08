"""乐高艺术海报风核心：为每张图自动选择“最优官方色子集”。

思路（官方艺术套装工程化）：逐格从全库最近色容易“杂”，先找到图片的
K 个主导色（k-means），再用加权贪心从官方色里挑出 K 个最能覆盖这些
主导色的颜色 —— 只在这组子集里拼，整体和谐、件数可控。

choose_palette: cells(H,W,3) → (ids[K], Palette(子集))
"""

from __future__ import annotations

import numpy as np

from ..color import Palette
from ..color.convert import rgb_to_lab


def _weighted_kmeans(lab_flat: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """对 (N,3) Lab 像素做 k-means，返回 (centers(k,3), weights(k))。"""
    import cv2

    cv2.setRNGSeed(0)  # 确定性
    data = lab_flat.astype(np.float32)
    n = len(data)
    k = max(2, min(k, n))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 1.0)
    _, labels, centers = cv2.kmeans(data, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.ravel(), minlength=k).astype(np.float64)
    return centers.astype(np.float64), counts / max(counts.sum(), 1)


def choose_palette(
    cells: np.ndarray,
    palette: Palette,
    k: int,
    *,
    pool_ids: list[str] | None = None,
    sample_max: int = 24000,
) -> tuple[list[str], Palette]:
    """选择 k 个官方色；返回 (有序 ids, 子集 Palette)。

    步骤：主导色 k-means（K≈k×2）→ 按像素占比加权的贪心覆盖（每个新色
    最小化“主导色到已选集合”的加权最小距离）。
    """
    k = max(1, int(k))
    arr = np.asarray(cells, dtype=np.float64).reshape(-1, 3)
    if len(arr) > sample_max:
        rng = np.random.default_rng(1)
        arr = arr[rng.choice(len(arr), sample_max, replace=False)]
    lab = rgb_to_lab(arr)

    centers, weights = _weighted_kmeans(lab, min(len(arr), max(2, k * 2)))

    ids = pool_ids or list(palette.ids)
    pal_lab = palette.lab
    idx_of = {cid: i for i, cid in enumerate(palette.ids)}
    cand_idx = [i for i in range(len(ids)) if ids[i] in idx_of]
    # 中心 ↔ 官方候选 距离（E76 近似，供贪心排序）
    dl = centers[:, None, 0] - pal_lab[None, :, 0]
    da = centers[:, None, 1] - pal_lab[None, :, 1]
    db = centers[:, None, 2] - pal_lab[None, :, 2]
    dist = np.sqrt(dl * dl + da * da + db * db)  # (n_c, N_pal)
    dist = dist[:, cand_idx]
    cand_ids = [ids[i] for i in cand_idx]

    chosen_idx: list[int] = []
    min_d = np.full(len(centers), np.inf)
    need = min(k, len(cand_ids))
    while len(chosen_idx) < need:
        improve = np.zeros(len(cand_ids))
        for c in range(len(cand_ids)):
            if c in chosen_idx:  # 排除已选
                improve[c] = np.inf
                continue
            nd = np.minimum(min_d, dist[:, c])
            improve[c] = float((weights * nd).sum())
        best = int(np.argmin(improve))
        chosen_idx.append(best)
        min_d = np.minimum(min_d, dist[:, best])
    chosen = [cand_ids[i] for i in chosen_idx]
    specs = [palette.get(cid) for cid in chosen]
    subset = Palette(specs)  # type: ignore[list-item]
    return chosen, subset
