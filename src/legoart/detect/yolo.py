"""YOLO 适配器（Ultralytics）—— 有模型 + 已安装 ultralytics 时启用。

检测/分割每个积木实例：mask 平均色 → 最近官方色候选。
注意：ultralytics + torch 需另行安装（见 pyproject [ml] extra 与
scripts/fetch_models.py yolo）。未安装/无权重时由 resolve_detector 降级到
ColorSegDetector（D12 口径不变：形态仍需用户下拉确认）。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..color import Palette
from .base import PartCandidate


class YoloDetector:
    kind = "yolo"

    def __init__(self, model_path: str | Path, palette: Palette, *, conf: float = 0.4) -> None:
        from ultralytics import YOLO  # 延迟导入

        self.model = YOLO(str(model_path))
        self.palette = palette
        self.conf = conf

    def predict(self, rgb: np.ndarray) -> list[PartCandidate]:
        arr = np.asarray(rgb, dtype=np.uint8)
        results = self.model(arr, conf=self.conf, verbose=False)
        out: list[PartCandidate] = []
        for r in results:
            if r.masks is None:
                continue
            for i, seg in enumerate(r.masks.data):  # (N,H,W) bool/np
                mask = np.asarray(seg.cpu().numpy(), dtype=bool)
                if not mask.any():
                    continue
                ys, xs = np.nonzero(mask)
                x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
                sub = arr[y0:y1, x0:x1]
                if sub.size == 0:
                    continue
                avg = tuple(int(v) for v in sub.reshape(-1, 3).mean(axis=0))
                cid, de = self.palette.nearest(np.array([avg], dtype=np.float64), color_set="all")
                out.append(
                    PartCandidate(
                        x=x0, y=y0, w=x1 - x0, h=y1 - y0,
                        area=int(mask.sum()), avg_rgb=avg,
                        palette_color_id=str(cid[0]), delta=float(de[0]),
                        label="yolo",
                    )
                )
        out.sort(key=lambda c: -c.area)
        return out
