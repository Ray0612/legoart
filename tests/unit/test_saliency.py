"""显著性测试：对比度实现 / 区域提取 / 降级解析。"""

import numpy as np

from legoart.model import Region
from legoart.saliency import ContrastSaliency, extract_regions, resolve_provider


def test_contrast_uniform_zero():
    rgb = np.full((16, 16, 3), 128.0)
    s = ContrastSaliency().predict(rgb)
    assert np.all(s == 0.0)


def test_contrast_highlights_square():
    rgb = np.full((64, 64, 3), 120.0)
    rgb[20:36, 20:36] = (230.0, 40.0, 30.0)
    s = ContrastSaliency().predict(rgb)
    inner = s[24:32, 24:32].mean()
    outer = np.concatenate([s[2:10].ravel(), s[-10:-2].ravel()]).mean()
    assert inner > outer * 3


def test_extract_regions_center():
    score = np.zeros((20, 20))
    score[6:14, 6:14] = 0.9
    regions = extract_regions(score)
    assert regions
    r = regions[0]
    assert isinstance(r, Region)
    assert r.source == "ai"
    assert 1 <= r.raise_layers <= 3
    assert r.mask[10, 10]  # 中心被覆盖


def test_extract_filters_tiny():
    score = np.zeros((20, 20))
    score[0, 0] = 0.9
    regions = extract_regions(score, min_area_frac=0.05)  # 需要 ≥20 格
    assert regions == []


def test_extract_uniform_empty():
    assert extract_regions(np.zeros((10, 10))) == []


def test_resolve_defaults_to_contrast(monkeypatch):
    monkeypatch.delenv("LEGOART_SALIENCY_MODEL", raising=False)
    prov, used_ai = resolve_provider()
    assert used_ai is False
    assert prov.kind == "contrast"
