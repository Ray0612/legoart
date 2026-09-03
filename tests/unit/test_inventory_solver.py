"""库存约束求解测试：精确/近似色/可铺缩替代/缺件/极限。"""

import numpy as np
import pytest

from legoart import api
from legoart.inventory import solve_inventory
from legoart.model import PartPlacement
from legoart.model.image_spec import ShortageStrategy


@pytest.fixture(scope="module")
def ctx():
    cat = api.load_catalog()
    return cat, api.build_palette(cat)


def _p(design, color, w, h, x=0, y=0, layer=0):
    return PartPlacement(design, color, layer, x, y, w, h)


def test_exact_consumes(ctx):
    cat, pal = ctx
    demand = [_p("3020", "Red", 4, 2), _p("3023", "Blue", 2, 1)]
    stock = {("3020", "Red"): 1, ("3023", "Blue"): 3}
    r = solve_inventory(
        demand, stock, strategy=ShortageStrategy.MISSING_LIST, catalog=cat, palette=pal
    )
    assert len(r.placements) == 2
    assert r.missing == []
    assert sorted(r.allocations) == [("3020", "Red", 1), ("3023", "Blue", 1)]


def test_approx_same_shape_other_color(ctx):
    cat, pal = ctx
    demand = [_p("3020", "Red", 4, 2)]
    stock = {("3020", "Blue"): 1}
    r = solve_inventory(demand, stock, strategy=ShortageStrategy.APPROXIMATE, catalog=cat, palette=pal)
    assert len(r.placements) == 1
    p = r.placements[0]
    assert p.design_id == "3020" and p.color_id == "Blue"
    assert r.missing == []
    assert r.allocations == [("3020", "Blue", 1)]
    assert r.substituted and r.substituted[0][1] == "3020" and r.substituted[0][3] == "Blue"


def test_approx_picks_nearest_color(ctx):
    cat, pal = ctx
    demand = [_p("3020", "Red", 4, 2)]
    stock = {("3020", "Blue"): 1, ("3020", "Dark Red"): 2}
    r = solve_inventory(demand, stock, strategy=ShortageStrategy.APPROXIMATE, catalog=cat, palette=pal)
    # Red 与 Dark Red 更近 → 应选 Dark Red
    assert r.placements[0].color_id == "Dark Red"
    assert r.allocations == [("3020", "Dark Red", 1)]


def test_tile_substitute_1x4_to_1x2(ctx):
    cat, pal = ctx
    demand = [_p("3710", "White", 4, 1)]  # Plate 1×4
    stock = {("3023", "White"): 2, ("3024", "White"): 10}  # 1×2 与 1×1
    r = solve_inventory(demand, stock, strategy=ShortageStrategy.APPROXIMATE, catalog=cat, palette=pal)
    assert len(r.placements) == 2  # 2× Plate 1×2 铺满
    assert all(p.design_id == "3023" for p in r.placements)
    assert r.allocations == [("3023", "White", 2)]
    # 锚点覆盖原 footprint 且无重叠
    cells = sorted((p.x, p.y) for p in r.placements)
    assert cells == [(0, 0), (2, 0)]


def test_missing_list_keeps_original(ctx):
    cat, pal = ctx
    demand = [_p("3020", "Red", 4, 2), _p("3024", "White", 1, 1)]
    stock = {("3020", "Red"): 1}  # 缺 1×1
    r = solve_inventory(demand, stock, strategy=ShortageStrategy.MISSING_LIST, catalog=cat, palette=pal)
    assert len(r.placements) == 1
    assert any(m.design_id == "3024" and m.color_id == "White" and m.qty == 1 for m in r.missing)
    assert r.allocations == [("3020", "Red", 1)]
    assert r.warnings


def test_extreme_partial_only(ctx):
    cat, pal = ctx
    demand = [_p("3024", "Red", 1, 1), _p("3024", "Red", 1, 1)]
    stock = {("3024", "Red"): 1}
    r = solve_inventory(demand, stock, strategy=ShortageStrategy.EXTREME, catalog=cat, palette=pal)
    assert len(r.placements) == 1
    assert len(r.missing) == 1
    assert r.allocations == [("3024", "Red", 1)]


def test_approx_no_fallback_missing(ctx):
    cat, pal = ctx
    demand = [_p("3020", "Red", 4, 2)]
    r = solve_inventory(demand, {}, strategy=ShortageStrategy.APPROXIMATE, catalog=cat, palette=pal)
    assert r.placements == []
    assert len(r.missing) == 1


def test_empty_demand(ctx):
    cat, pal = ctx
    r = solve_inventory([], {}, strategy=ShortageStrategy.MISSING_LIST, catalog=cat, palette=pal)
    assert r.placements == [] and r.missing == [] and r.allocations == []
