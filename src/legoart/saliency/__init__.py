"""显著性/重点识别（D6）。Provider 抽象 + 内置离线实现 + 未来 U²-Net 适配器。"""

from .base import RegionExtractor, SaliencyProvider, extract_regions
from .contrast import ContrastSaliency
from .resolve import resolve_provider

__all__ = [
    "SaliencyProvider",
    "RegionExtractor",
    "extract_regions",
    "ContrastSaliency",
    "resolve_provider",
]
