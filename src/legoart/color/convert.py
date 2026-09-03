"""sRGB ↔ CIE L*a*b*（D65）转换，Numpy 向量化。

约定：RGB 通道为 float 0..255（也可传 uint8）；Lab 为标准范围
（L 0..100，a/b 无界）。转换矩阵取自 IEC 61966-2-1 (sRGB) + D65。
"""

from __future__ import annotations

import numpy as np

# sRGB -> XYZ（D65）矩阵（行主序：每行对应 R/G/B 的系数）
_M_SRGB = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)

_WHITE = np.array([0.95047, 1.0, 1.08883], dtype=np.float64)  # D65

_DELTA = 6.0 / 29.0
_DELTA_CUBE = _DELTA ** 3
_SLOPE = 1.0 / (3.0 * _DELTA * _DELTA)  # 约 0.12841855
_OFFSET = 4.0 / 29.0


def _lin(c: np.ndarray) -> np.ndarray:
    """sRGB 非线性值(0..1) -> 线性光。"""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _srgb(c: np.ndarray) -> np.ndarray:
    """线性光 -> sRGB 非线性值(0..1)。"""
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.sign(c) * np.abs(c) ** (1 / 2.4) - 0.055)


def _f(t: np.ndarray) -> np.ndarray:
    """Lab 压缩函数。"""
    return np.where(t > _DELTA_CUBE, np.cbrt(t), _SLOPE * t + _OFFSET)


def _f_inv(t: np.ndarray) -> np.ndarray:
    return np.where(t > _DELTA, t ** 3, (t - _OFFSET) / _SLOPE)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """(..., 3) RGB(0..255) -> (..., 3) Lab。"""
    arr = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = _lin(arr)
    xyz = lin @ _M_SRGB.T
    fx = _f(xyz[..., 0] / _WHITE[0])
    fy = _f(xyz[..., 1] / _WHITE[1])
    fz = _f(xyz[..., 2] / _WHITE[2])
    lab = np.empty_like(xyz)
    lab[..., 0] = 116.0 * fy - 16.0
    lab[..., 1] = 500.0 * (fx - fy)
    lab[..., 2] = 200.0 * (fy - fz)
    return lab


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """(..., 3) Lab -> (..., 3) RGB(0..255, float)。"""
    arr = np.asarray(lab, dtype=np.float64)
    fy = (arr[..., 0] + 16.0) / 116.0
    fx = fy + arr[..., 1] / 500.0
    fz = fy - arr[..., 2] / 200.0
    xyz = np.stack(
        [_WHITE[0] * _f_inv(fx), _WHITE[1] * _f_inv(fy), _WHITE[2] * _f_inv(fz)], axis=-1
    )
    lin = xyz @ np.linalg.inv(_M_SRGB).T
    rgb = _srgb(lin) * 255.0
    return np.clip(rgb, 0.0, 255.0)
