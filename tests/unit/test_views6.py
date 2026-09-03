"""6 视角投影测试。"""

import numpy as np

from legoart.model import GridModel, LayerStack
from legoart.export.views6 import bottom_grid, overview_grid, side_grid, top_grid


def _stack():
    g0 = GridModel(2, 2, np.array([["Red", "Red"], ["Red", "Red"]], dtype=object))
    g1 = GridModel(2, 2, np.array([["White", ""], ["", ""]], dtype=object))
    stack = LayerStack(2, 2)
    stack.add(0, g0)
    stack.add(1, g1)
    return stack


def test_top_grid_levels():
    s = _stack()
    t0 = top_grid(s, 0)
    assert t0.colors.tolist() == [["Red", "Red"], ["Red", "Red"]]
    t1 = top_grid(s, 1)
    assert t1.colors.tolist() == [["White", ""], ["", ""]]


def test_overview_topmost():
    s = _stack()
    assert overview_grid(s) == [["White", "Red"], ["Red", "Red"]]


def test_bottom_mirrored():
    s = _stack()
    assert bottom_grid(s) == [["Red", "Red"], ["Red", "Red"]]


def test_front_projection_hides_behind():
    s = _stack()
    # 拼到 L0：只看底层 → 一"行"宽=W
    assert side_grid(s, 0, "front") == [["Red", "Red"]]
    # 拼到 L1：(x0,z1)=White；x1 z1 空
    assert side_grid(s, 1, "front") == [["Red", "Red"], ["White", ""]]


def test_side_directions_len():
    s = _stack()
    for ax in ("front", "back", "left", "right"):
        g = side_grid(s, 1, ax)
        # 每行长度 = 沿向维度
        assert all(len(r) == len(g[0]) for r in g)
    # back 与 front 在 L1 上对称（区域在 x0）: back z1 也在 x0
    assert side_grid(s, 1, "back") == side_grid(s, 1, "front")
