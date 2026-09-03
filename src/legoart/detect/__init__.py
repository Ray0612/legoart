"""拍照识别适配器（D12/M6）：无模型色块分割兜底可用，YOLO 权重就绪后自动优先。"""

from .base import PartCandidate, PhotoDetector
from .opencv_seg import ColorSegDetector, build_default_detector
from .resolve import resolve_detector

__all__ = ["PartCandidate", "PhotoDetector", "ColorSegDetector", "build_default_detector", "resolve_detector"]
