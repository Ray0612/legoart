"""采样：把（已裁剪的）源图映射为 W×H 格的每格代表色（D3：网格即分辨率）。

实现：``Image.resize(..., BOX)``（面积平均，C 实现、向量化）；
可选对格矩阵做 3×3 中值降噪，抑制单格椒盐噪色。
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from ..errors import DataError


def load_rgb_image(path_or_bytes) -> Image.Image:
    """打开图片并做 EXIF 方向修正、转 RGB；失败抛 DataError。"""
    try:
        im = Image.open(path_or_bytes)
        im = ImageOps_exif_transpose(im)
        return im.convert("RGB")
    except Exception as e:  # OSError / UnidentifiedImageError 等
        raise DataError(f"图片无法读取: {e}") from e


def ImageOps_exif_transpose(im: Image.Image) -> Image.Image:
    try:
        from PIL import ImageOps

        return ImageOps.exif_transpose(im)
    except Exception:
        return im  # 旧版 Pillow 无此方法时原样返回


def sample_grid(image: Image.Image, width: int, height: int, *, median_ksize: int = 0) -> np.ndarray:
    """返回 (height, width, 3) float 每格代表色（0..255）。

    采样语义：BOX 平均 = 每格取源图对应区域的面积平均色。
    median_ksize 默认 0（关闭）：3×3 中值会吞掉 1~2 格宽的细结构
    （如线稿黑边/点状星点），造成细节丢失；如需抑制椒盐噪色可显式传 3/5。
    """
    if width < 1 or height < 1:
        raise DataError(f"网格尺寸非法: {width}x{height}")
    if width > 4096 or height > 4096:
        raise DataError(f"网格过大（{width}x{height}），超过 4096 上限")
    rgb = image.convert("RGB")
    small = rgb.resize((width, height), Image.Resampling.BOX)
    cells = np.asarray(small, dtype=np.float64)  # (height, width, 3)
    if median_ksize and min(height, width) >= 3:
        cells = _median_cells(cells, median_ksize)
    return cells


def _median_cells(cells: np.ndarray, ksize: int) -> np.ndarray:
    """对每格色做通道独立中值滤波（须 3x3 以上尺寸；依赖 opencv 时用其加速）。"""
    if ksize % 2 == 0 or ksize < 3:
        raise DataError(f"median_ksize 须为 ≥3 的奇数: {ksize}")
    try:
        import cv2  # type: ignore

        out = cv2.medianBlur(cells.astype(np.float32), ksize)
        return np.clip(out, 0.0, 255.0).astype(np.float64)
    except ImportError:
        return _median_cells_pure(cells, ksize)


def _median_cells_pure(cells: np.ndarray, ksize: int) -> np.ndarray:
    """纯 numpy 中值（性能弱于 cv2，作为无 opencv 兜底）。"""
    from numpy.lib.stride_tricks import sliding_window_view

    pad = ksize // 2
    out = np.empty_like(cells)
    for c in range(3):
        ch = cells[..., c]
        ch = np.pad(ch, pad, mode="edge")
        win = sliding_window_view(ch, (ksize, ksize))
        out[..., c] = np.median(win, axis=(-2, -1))
    return out
