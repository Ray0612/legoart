"""CIEDE2000 色差（Sharma, Wu & Dalal 2005），Numpy 向量化实现。

- ``delta_e00``       : 同形/可广播的两组 Lab，逐元素色差；
- ``delta_e00_pairwise`` : Lab1 (M,3) × Lab2 (N,3) 全距阵 (M,N)。

性能策略（技术方案 §6.1）：大网格场景先用 CIE76 粗筛取 top-K，
再对候选子集做精确 ΔE00 —— 由 ``Palette.nearest`` 负责编排，
本模块只保证单点公式与向量化正确。
"""

from __future__ import annotations

import numpy as np

_25_7 = 25.0 ** 7


def _delta_e00_impl(
    l1: np.ndarray,
    a1: np.ndarray,
    b1: np.ndarray,
    l2: np.ndarray,
    a2: np.ndarray,
    b2: np.ndarray,
    kl: float,
    kc: float,
    kh: float,
) -> np.ndarray:
    c1 = np.hypot(a1, b1)
    c2 = np.hypot(a2, b2)

    # G 因子：a* 轴压缩
    cbar = (c1 + c2) / 2.0
    cbar7 = cbar ** 7
    g = 0.5 * (1.0 - np.sqrt(cbar7 / (cbar7 + _25_7)))

    a1p = (1.0 + g) * a1
    a2p = (1.0 + g) * a2
    c1p = np.hypot(a1p, b1)
    c2p = np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    dlp = l2 - l1
    dcp = c2p - c1p

    c1c2 = c1p * c2p
    zero_c = c1c2 == 0.0  # 任一色度为零时，色相角相关项按 0/约定处理

    dh = h2p - h1p
    dh = np.where(dh > 180.0, dh - 360.0, dh)
    dh = np.where(dh < -180.0, dh + 360.0, dh)
    dhp = 2.0 * np.sqrt(c1c2) * np.sin(np.deg2rad(dh) / 2.0)
    dhp = np.where(zero_c, 0.0, dhp)

    lbarp = (l1 + l2) / 2.0
    cbarp = (c1p + c2p) / 2.0

    # 平均色相角（处理 0/360 环绕）
    hsum = h1p + h2p
    hdiff = h2p - h1p
    hbar = hsum / 2.0
    cross = (~zero_c) & (np.abs(hdiff) > 180.0)
    hbar = np.where(cross, np.where(hsum < 360.0, (hsum + 360.0) / 2.0, (hsum - 360.0) / 2.0), hbar)
    hbar = np.where(zero_c, hsum, hbar)

    t = (
        1.0
        - 0.17 * np.cos(np.deg2rad(hbar - 30.0))
        + 0.24 * np.cos(np.deg2rad(2.0 * hbar))
        + 0.32 * np.cos(np.deg2rad(3.0 * hbar + 6.0))
        - 0.20 * np.cos(np.deg2rad(4.0 * hbar - 63.0))
    )
    dtheta = 30.0 * np.exp(-(((hbar - 275.0) / 25.0) ** 2))
    cbarp7 = cbarp ** 7
    rc = 2.0 * np.sqrt(cbarp7 / (cbarp7 + _25_7))

    lm = lbarp - 50.0
    sl = 1.0 + 0.015 * (lm * lm) / np.sqrt(20.0 + lm * lm)
    sc = 1.0 + 0.045 * cbarp
    sh = 1.0 + 0.015 * cbarp * t
    rt = -np.sin(np.deg2rad(2.0 * dtheta)) * rc

    t1 = dlp / (kl * sl)
    t2 = dcp / (kc * sc)
    t3 = dhp / (kh * sh)
    return np.sqrt(t1 * t1 + t2 * t2 + t3 * t3 + rt * t2 * t3)


def delta_e00(lab1: np.ndarray, lab2: np.ndarray, *, kl: float = 1.0, kc: float = 1.0, kh: float = 1.0) -> np.ndarray:
    """两组可广播的 Lab（..., 3）的逐元素 ΔE00（...）。"""
    a1 = np.asarray(lab1, dtype=np.float64)
    a2 = np.asarray(lab2, dtype=np.float64)
    return _delta_e00_impl(
        a1[..., 0], a1[..., 1], a1[..., 2],
        a2[..., 0], a2[..., 1], a2[..., 2],
        kl, kc, kh,
    )


def delta_e00_pairwise(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """Lab1 (M,3) × Lab2 (N,3) 的 ΔE00 全距阵 (M,N)。"""
    a = np.asarray(lab1, dtype=np.float64)
    b = np.asarray(lab2, dtype=np.float64)
    return _delta_e00_impl(
        a[:, 0:1], a[:, 1:2], a[:, 2:3],
        b[np.newaxis, :, 0], b[np.newaxis, :, 1], b[np.newaxis, :, 2],
        1.0, 1.0, 1.0,
    )
