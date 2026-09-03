"""Palette 测试：装载 / 最近色匹配 / color_set 过滤。"""

import numpy as np
import pytest

from legoart.catalog.models import ColorSpec
from legoart.color import Palette


def _specs():
    return [
        ColorSpec("White", "White", "White", "#FFFFFF", recommended=True),
        ColorSpec("Red", "Red", "Bright Red", "#C91A09", recommended=True),
        ColorSpec("Black", "Black", "Black", "#05131D", recommended=False),
        ColorSpec("Trans-Red", "Trans-Red", "", "#C91A09", is_trans=True, material="transparent", recommended=False),
    ]


def test_load_and_index():
    p = Palette(_specs())
    assert len(p) == 4
    assert "Red" in p
    assert p.rgb.shape == (4, 3)
    assert list(p.recommended_ids) == ["White", "Red"]


def test_nearest_exact():
    p = Palette(_specs())
    ids, de = p.nearest(np.array([[255.0, 255.0, 255.0], [201.0, 26.0, 9.0]]), color_set="all")
    assert list(ids) == ["White", "Red"]
    np.testing.assert_allclose(de, [0.0, 0.0], atol=1e-6)


def test_nearest_red_vs_gray_palette():
    p = Palette(_specs())
    # 纯红查询在全色集中应命中 Red
    ids, _ = p.nearest(np.array([[200.0, 10.0, 5.0]]), color_set="all")
    assert ids[0] == "Red"


def test_color_set_recommended_excludes_black():
    p = Palette(_specs())
    # 黑色查询在 recommended 集中应命中 White/Red 之一（绝不会是 Black）
    ids, _ = p.nearest(np.array([[3.0, 5.0, 10.0]]), color_set="recommended")
    assert ids[0] != "Black"
    # all 集中应命中 Black
    ids2, _ = p.nearest(np.array([[3.0, 5.0, 10.0]]), color_set="all")
    assert ids2[0] == "Black"


def test_nearest_unknown_color_list_raises():
    p = Palette(_specs())
    with pytest.raises(ValueError):
        p.nearest(np.array([[0.0, 0.0, 0.0]]), color_set=["Nope"])


def test_nearest_bad_shape_raises():
    p = Palette(_specs())
    with pytest.raises(ValueError):
        p.nearest(np.zeros((4,), dtype=np.float64))


def test_large_batch_performance():
    """2304 格 × 4 色的匹配应在毫秒级（性能基线，宽松断言）。"""
    import time

    p = Palette(_specs())
    rng = np.random.default_rng(0)
    q = rng.random((2304, 3)) * 255.0
    t0 = time.perf_counter()
    ids, de = p.nearest(q, color_set="all")
    dt = time.perf_counter() - t0
    assert ids.shape == (2304,)
    assert de.shape == (2304,)
    assert dt < 5.0, f"匹配耗时异常: {dt:.3f}s"
