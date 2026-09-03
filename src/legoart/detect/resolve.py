"""检测器解析：YOLO（模型+ultralytics 就绪）优先，否则 opencv 分割兜底。"""

from __future__ import annotations

import os
from pathlib import Path

from ..api import load_catalog
from ..color import Palette
from .base import PhotoDetector
from .opencv_seg import ColorSegDetector


def _model_path() -> Path | None:
    env = os.environ.get("LEGOART_DETECTOR_MODEL")
    if env:
        p = Path(env)
        if p.exists():
            return p
    here = Path(__file__).resolve()
    repo = here.parents[3] / "data" / "models" / "yolo.pt"
    return repo if repo.exists() else None


def resolve_detector(palette: Palette | None = None) -> tuple[PhotoDetector, bool]:
    """返回 (detector, used_ai)。YOLO 不可用 → ColorSegDetector + used_ai=False。"""
    pal = palette
    if pal is None:
        cat = load_catalog()
        pal = Palette([c for c in cat.colors if not c.is_trans])
    mp = _model_path()
    if mp is not None:
        try:
            from .yolo import YoloDetector

            return YoloDetector(mp, pal), True
        except Exception:
            pass
    return ColorSegDetector(pal), False
