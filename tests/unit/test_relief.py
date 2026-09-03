"""relief / 凸起分层测试。"""

import numpy as np
import pytest

from legoart.errors import DataError
from legoart.model import GridModel, Region
from legoart.mosaic.relief import build_layer_stack


def _base():
    return GridModel(3, 3, np.array([["Red"] * 3] * 3, dtype=object))


def test_no_regions_single_layer():
    stack = build_layer_stack(_base(), [])
    assert stack.height_total == 1
    assert stack.level_grid(0) is not None


def test_center_raise_two_layers():
    mask = np.zeros((3, 3), dtype=bool)
    mask[1, 1] = True
    stack = build_layer_stack(_base(), [Region(mask=mask, raise_layers=2, source="ai")])
    assert stack.height_total == 3
    g0 = stack.level_grid(0)
    g1 = stack.level_grid(1)
    g2 = stack.level_grid(2)
    assert g0.colors[1, 1] == "Red"
    assert g1.colors[1, 1] == "Red" and g1.colors[0, 0] == ""
    assert g2.colors[1, 1] == "Red" and g2.colors[2, 2] == ""


def test_overlap_region_higher_wins():
    big = np.zeros((3, 3), dtype=bool)
    big[:, :] = True
    center = np.zeros((3, 3), dtype=bool)
    center[1, 1] = True
    base = GridModel(3, 3, np.array([["Red"] * 3] * 3, dtype=object))
    stack = build_layer_stack(
        base, [Region(mask=big, raise_layers=1, source="ai"), Region(mask=center, raise_layers=2, source="ai")]
    )
    assert stack.height_total == 3
    assert stack.level_grid(2).colors[1, 1] == "Red"
    assert stack.level_grid(2).colors[0, 0] == ""


def test_bad_mask_shape_raises():
    mask = np.zeros((2, 2), dtype=bool)
    with pytest.raises(DataError):
        build_layer_stack(_base(), [Region(mask=mask, raise_layers=1)])


def test_bad_raise_layers_raises():
    mask = np.zeros((3, 3), dtype=bool)
    mask[0, 0] = True
    with pytest.raises(DataError):
        build_layer_stack(_base(), [Region(mask=mask, raise_layers=0)])
