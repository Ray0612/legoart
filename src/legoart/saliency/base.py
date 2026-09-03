"""Saliency 抽象与区域提取（纯 numpy，依赖 cv2 做连通域/形态学）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ..model import Region


class SaliencyProvider(Protocol):
    """输入 (H, W, 3) RGB uint8/float(0..255) → 显著性分数 (H, W) 0..1。"""

    kind: str

    def predict(self, rgb: np.ndarray) -> np.ndarray: ...


@dataclass(slots=True)
class RegionExtractor:
    """把网格分辨率的分数图切成凸起区域（O7 默认：分数分档 1–3 层）。"""

    min_area_frac: float = 0.002  # 小于网格 0.2% 的区域丢弃
    kernel: int = 3

    def run(self, score: np.ndarray) -> list[Region]:
        import cv2

        s = np.asarray(score, dtype=np.float64)
        if s.ndim != 2 or s.size == 0:
            return []
        # Otsu 自适应阈值（分数归一化 0..1 → 8bit）
        u8 = np.clip(s * 255.0, 0, 255).astype(np.uint8)
        if int(u8.max()) <= int(u8.min()):  # 无对比 → 无区域
            return []
        _, mask = cv2.threshold(u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        k = self.kernel
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
        # 先膨胀：把 1 格宽的边缘响应"填充"进实心区域内部，避免缩小后碎裂
        mask = cv2.dilate(mask, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        n, labels = cv2.connectedComponents(mask)
        h, w = s.shape
        min_area = int(self.min_area_frac * h * w)
        regions: list[Region] = []
        for i in range(1, n):
            m = labels == i
            if int(m.sum()) < min_area:
                continue
            mean = float(s[m].mean())
            raise_layers = min(3, max(1, int(round(mean * 3.0))))
            regions.append(Region(mask=m, raise_layers=raise_layers, source="ai", score=mean))
        regions.sort(key=lambda r: -r.score)
        return regions


def extract_regions(score: np.ndarray, **kw) -> list[Region]:
    return RegionExtractor(**kw).run(score)
