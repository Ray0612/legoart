"""无模型兜底检测：Lab + k-means 颜色分割 → 连通域 → 官方色候选。

启发式前提：散落积木照片中每个积木 ≈ 均匀颜色连通块。
过滤规则：
- 太大（>背景占比 max_bg_frac）视作背景/桌面 → 丢弃；
- 太小（<min_area_frac·总面积）→ 噪点丢弃；
- 平均色离任何官方色太远（>max_delta ΔE00）→ 非积木色丢弃。
"""

from __future__ import annotations

import numpy as np

from ..catalog.models import ColorSpec
from ..color import Palette
from .base import PartCandidate


class ColorSegDetector:
    kind = "opencv-seg"

    def __init__(
        self,
        palette: Palette,
        *,
        k: int = 5,
        min_area_frac: float = 0.001,
        max_bg_frac: float = 0.5,
        max_delta: float = 28.0,
        max_side: int = 640,
    ) -> None:
        self.palette = palette
        self.k = k
        self.min_area_frac = min_area_frac
        self.max_bg_frac = max_bg_frac
        self.max_delta = max_delta
        self.max_side = max_side

    def predict(self, rgb: np.ndarray) -> list[PartCandidate]:
        import cv2

        arr = np.asarray(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]
        if h == 0 or w == 0:
            return []
        scale = min(1.0, self.max_side / max(w, h))
        if scale < 1.0:
            arr = cv2.resize(arr, (max(1, round(w * scale)), max(1, round(h * scale))),
                             interpolation=cv2.INTER_AREA)
            h, w = arr.shape[:2]

        lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
        pixels = lab.reshape(-1, 3).astype(np.float32)
        k = min(self.k, max(1, len(pixels) // 64))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS
        )
        labels_img = labels.reshape(h, w)

        total = h * w
        out: list[PartCandidate] = []
        for ci in range(k):
            mask_u8 = (labels_img == ci).astype(np.uint8)
            n, labl, stats, _ = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)
            avg_rgb = tuple(int(v) for v in np.mean(
                arr.reshape(-1, 3)[labels.ravel() == ci], axis=0
            ))
            for i in range(1, n):
                x, y, cw, ch, area = (int(v) for v in stats[i])
                if area < self.min_area_frac * total:
                    continue
                if area > self.max_bg_frac * total:
                    continue  # 背景/桌面
                if area == 0:
                    continue
                color_id, de = self._nearest(avg_rgb)
                if de > self.max_delta:
                    continue
                out.append(
                    PartCandidate(
                        x=x, y=y, w=cw, h=ch, area=area,
                        avg_rgb=avg_rgb, palette_color_id=color_id, delta=float(de),
                    )
                )
        # 面积降序，稳定输出
        out.sort(key=lambda c: -c.area)
        return out

    def _nearest(self, rgb) -> tuple[str, float]:
        ids, de = self.palette.nearest(np.array([rgb], dtype=np.float64), color_set="all")
        return str(ids[0]), float(de[0])


def build_default_detector(catalog_colors: list[ColorSpec] | None = None) -> ColorSegDetector:
    """用目录色（实色、推荐）构建兜底检测器。"""
    from ..api import load_catalog

    specs = catalog_colors or load_catalog().colors
    solid = [c for c in specs if not c.is_trans]
    return ColorSegDetector(Palette(solid))
