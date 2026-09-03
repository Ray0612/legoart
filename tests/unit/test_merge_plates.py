"""merge_plates 测试：实心/棋盘/条带/L 形覆盖完备、确定性、缺 1×1 报错。"""

import numpy as np
import pytest

from legoart.catalog.models import PartSpec
from legoart.errors import DataError
from legoart.model import GridModel
from legoart.mosaic.merge_plates import merge_grid, merge_stats


def _plates(names):
    dims = {
        "3024": (1, 1), "3023": (1, 2), "3710": (1, 4), "3460": (1, 8),
        "3022": (2, 2), "3020": (2, 4), "3034": (2, 8), "3031": (4, 4),
    }
    out = []
    for n in names:
        w, h = dims[n]
        out.append(PartSpec(n, f"Plate {max(w,h)} x {min(w,h)}", "Plate", w, h, "plate"))
    return out


def _grid(rows):
    return GridModel(len(rows[0]), len(rows), np.array(rows, dtype=object))


def test_solid_4x4_with_4x4_plate():
    g = _grid([["Red"] * 4] * 4)
    ps = merge_grid(g, _plates(["3024", "3023", "3022", "3020", "3031"]))
    assert len(ps) == 1
    assert ps[0].area == 16 and ps[0].design_id == "3031"


def test_solid_4x4_without_4x4_plate():
    g = _grid([["Red"] * 4] * 4)
    ps = merge_grid(g, _plates(["3024", "3022", "3020"]))
    assert sum(p.area for p in ps) == 16
    assert len(ps) == 2  # 两个 2×4（旋转 4×2 摆放）
    assert all(p.design_id == "3020" for p in ps)


def test_checkerboard_all_1x1():
    rows = [["Red" if (x + y) % 2 == 0 else "White" for x in range(4)] for y in range(4)]
    g = _grid(rows)
    ps = merge_grid(g, _plates(["3024"]))
    assert len(ps) == 16
    assert all(p.area == 1 for p in ps)


def test_stripe_2x8_single_plate():
    g = _grid([["Blue"] * 8] * 2)
    ps = merge_grid(g, _plates(["3024", "3022", "3034"]))
    assert len(ps) == 1 and ps[0].design_id == "3034" and ps[0].area == 16


def test_l_shape_coverage_matches():
    rows = [
        ["Red", "Blue", "Blue"],
        ["Red", "Red", "Blue"],
        ["Red", "Red", "Blue"],
    ]
    g = _grid(rows)
    ps = merge_grid(g, _plates(["3024", "3023", "3022", "3020"]))
    cover = np.zeros((3, 3), dtype=bool)
    for p in ps:
        cover[p.y : p.y + p.h, p.x : p.x + p.w] = True
    assert cover.all()  # 覆盖完备
    assert sum(p.area for p in ps) == 9


def test_deterministic():
    rng = np.random.default_rng(3)
    ids = ["Red", "White", "Blue"]
    rows = [[ids[rng.integers(0, 3)] for _ in range(8)] for _ in range(6)]
    g = _grid(rows)
    ps1 = merge_grid(g, _plates(["3024", "3023", "3710", "3022", "3020"]))
    ps2 = merge_grid(g, _plates(["3024", "3023", "3710", "3022", "3020"]))
    assert [(p.layer, p.design_id, p.x, p.y, p.w, p.h, p.color_id) for p in ps1] == [
        (p.layer, p.design_id, p.x, p.y, p.w, p.h, p.color_id) for p in ps2
    ]


def test_empty_cells_ignored():
    rows = [["Red", "", "Red"]]
    g = _grid(rows)
    ps = merge_grid(g, _plates(["3024", "3023"]))
    assert sum(p.area for p in ps) == 2  # 两个 1×1，空格不覆盖
    assert all(p.w == 1 and p.h == 1 for p in ps)


def test_missing_1x1_raises():
    g = _grid([["Red"]])
    with pytest.raises(DataError):
        merge_grid(g, _plates(["3020"]))  # 白名单无 1×1


def test_stats():
    g = _grid([["Red"] * 4] * 4)
    ps = merge_grid(g, _plates(["3024", "3020", "3031"]))
    s = merge_stats(ps, 16)
    assert s["parts"] == 1 and s["covered_cells"] == 16 and s["largest_area"] == 16


def test_performance_guard():
    """性能回归护栏：随机 48×48（2304 格）合并应在数秒内（历史最差 ~40s）。"""
    import time

    rng = np.random.default_rng(11)
    ids = ["Red", "White", "Blue", "Black", "Yellow", "Green"]
    rows = [[ids[rng.integers(0, len(ids))] for _ in range(48)] for _ in range(48)]
    g = _grid(rows)
    t0 = time.perf_counter()
    ps = merge_grid(g, _plates(["3024", "3023", "3710", "3460", "3022", "3020", "3034", "3031"]))
    dt = time.perf_counter() - t0
    assert dt < 5.0, f"merge 退化: {dt:.2f}s"
    assert sum(p.area for p in ps) == 48 * 48
