"""量化测试：格级最近色映射 + 残差。"""

import numpy as np
import pytest

from legoart.catalog.models import ColorSpec
from legoart.color import Palette
from legoart.errors import ColorError
from legoart.mosaic.quantize import quantize_grid


def _pal():
    return Palette(
        [
            ColorSpec("White", "White", "White", "#FFFFFF", recommended=True),
            ColorSpec("Red", "Red", "Bright Red", "#C91A09", recommended=True),
            ColorSpec("Blue", "Blue", "Bright Blue", "#0055BF", recommended=True),
            ColorSpec("Black", "Black", "Black", "#05131D", recommended=False),
        ]
    )


def test_exact_match():
    p = _pal()
    cells = np.array(
        [[[255, 255, 255], [201, 26, 9]], [[5, 19, 29], [0, 85, 191]]], dtype=np.float64
    )
    grid, deltas = quantize_grid(cells, p, color_set="all")
    assert grid.width == 2 and grid.height == 2
    assert grid.colors[0, 0] == "White"
    assert grid.colors[0, 1] == "Red"
    assert grid.colors[1, 0] == "Black"
    assert grid.colors[1, 1] == "Blue"
    np.testing.assert_allclose(deltas, 0.0, atol=1e-6)


def test_recommended_excludes_black():
    p = _pal()
    cells = np.array([[[3, 5, 10]]], dtype=np.float64)
    grid, _ = quantize_grid(cells, p, color_set="recommended")
    assert grid.colors[0, 0] != "Black"


def test_deterministic():
    p = _pal()
    rng = np.random.default_rng(1)
    cells = rng.random((16, 16, 3)) * 255.0
    g1, _ = quantize_grid(cells, p, color_set="all")
    g2, _ = quantize_grid(cells, p, color_set="all")
    np.testing.assert_array_equal(g1.colors, g2.colors)


def test_empty_raises():
    p = _pal()
    with pytest.raises(ColorError):
        quantize_grid(np.zeros((0, 3, 3)), p)


def test_bad_shape_raises():
    p = _pal()
    with pytest.raises(ColorError):
        quantize_grid(np.zeros((4, 4)), p)  # 缺颜色维
