"""Pipeline 端到端测试（M2：采样→量化→凸起分层→大板合并→按层 BOM）。"""

import json

import numpy as np
import pytest
from PIL import Image

from legoart import api
from legoart.errors import DataError, NotSupportedError
from legoart.model import ImageSpec, MosaicPlan, Region
from legoart.model.image_spec import StyleKind


def _gradient_image(w=320, h=160):
    """横向红→蓝渐变 + 底部白条。"""
    im = Image.new("RGB", (w, h))
    px = im.load()
    for x in range(w):
        r = int(255 * (1 - x / w))
        b = int(255 * x / w)
        for y in range(h):
            px[x, y] = (255, 255, 255) if y > int(h * 0.75) else (r, 0, b)
    return im


def _spec(w=48, h=24, saliency=False, **kw):
    return ImageSpec(grid_w=w, grid_h=h, style=StyleKind.COLOR_BLOCK, saliency_enabled=saliency, **kw)


def test_generate_full_plan():
    plan = api.generate_plan(_gradient_image(), _spec())
    assert isinstance(plan, MosaicPlan)
    assert plan.grid.width == 48 and plan.grid.height == 24
    assert plan.stack is not None and plan.stack.height_total == 1
    assert plan.placements, "应有合并后的板件"
    covered = sum(p.area for p in plan.placements)
    assert covered == 48 * 24  # 覆盖完备
    # 板型都来自内置白名单
    plate_ids = {p.design_id for p in api.load_catalog().plate_candidates()}
    assert {p.design_id for p in plan.placements} <= plate_ids
    # BOM 行 = 同类(层/件/色)去重，总量 = 板件数
    assert sum(i.qty for i in plan.bom.items) == len(plan.placements)
    assert all(i.layer is not None for i in plan.bom.items)
    assert plan.elapsed_ms >= 0


def test_merge_reduces_piece_count():
    # 纯色 24x24：合并件应远少于 1×1 的 576 片
    solid = Image.new("RGB", (96, 96), (200, 30, 20))
    plan = api.generate_plan(solid, _spec(24, 24))
    assert len(plan.placements) < 100
    assert len({p.color_id for p in plan.placements}) == 1


def test_multi_color_usage():
    plan = api.generate_plan(_gradient_image(), _spec())
    assert len(set(plan.grid.colors.ravel().tolist())) >= 2


def test_auto_height_from_aspect():
    spec = ImageSpec(grid_w=20, grid_h=0)  # 2:1 图 → h=10
    plan = api.generate_plan(_gradient_image(400, 200), spec)
    assert plan.grid.height == 10


def test_regions_create_raised_layers():
    solid = Image.new("RGB", (32, 32), (150, 40, 40))
    mask = np.zeros((8, 8), dtype=bool)
    mask[3:5, 3:5] = True
    regions = [Region(mask=mask, raise_layers=2, source="user")]
    plan = api.generate_plan(solid, _spec(8, 8), regions=regions)
    assert plan.stack.height_total == 3
    assert len(plan.regions.regions) == 1
    covered = sum(p.area for p in plan.placements)
    assert covered == 64 + 2 * 4  # 底层 64 + 两层各 4
    levels = {p.layer for p in plan.placements}
    assert levels == {0, 1, 2}


def test_style_not_supported_yet():
    spec = ImageSpec(grid_w=8, grid_h=8, style=StyleKind.TEXTURE)
    with pytest.raises(NotSupportedError):
        api.generate_plan(_gradient_image(32, 32), spec)


def test_bad_width():
    with pytest.raises(DataError):
        api.generate_plan(_gradient_image(), _spec(w=0))


def test_snapshot_json_roundtrip_fields(tmp_path):
    plan = api.generate_plan(_gradient_image(), _spec())
    out = tmp_path / "plan.json"
    out.write_text(json.dumps(plan.to_dict(), ensure_ascii=False), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["grid"]["w"] == 48
    assert len(loaded["stack"]) == 1
    assert loaded["bom"]
    assert loaded["placements"]
    assert loaded["spec"]["style"] == "color_block"


def test_progress_called():
    stages = []
    api.generate_plan(_gradient_image(), _spec(8, 8), progress=lambda s, f: stages.append(s))
    for stage in ("sample", "quantize", "relief", "merge", "done"):
        assert stage in stages


def test_saliency_degrade_warns_without_model(monkeypatch):
    monkeypatch.delenv("LEGOART_SALIENCY_MODEL", raising=False)
    solid = Image.new("RGB", (32, 32), (90, 90, 95))  # 均匀 → 无区域
    plan = api.generate_plan(solid, _spec(8, 8, saliency=True))
    assert any("saliency" in w for w in plan.warnings)
    assert len(plan.regions.regions) == 0


def test_color_set_all_uses_more_colors_than_recommended():
    from legoart.catalog.models import ColorSpec
    from legoart.color import Palette

    pal = Palette(
        [
            ColorSpec("White", "White", "White", "#FFFFFF", recommended=True),
            ColorSpec("Black", "Black", "Black", "#05131D", recommended=False),
        ]
    )
    dark = Image.new("RGB", (64, 64), (5, 7, 12))
    cat = api.load_catalog()
    p_rec = api.generate_plan(dark, _spec(8, 8, color_set="recommended"), palette=pal, catalog=cat)
    p_all = api.generate_plan(dark, _spec(8, 8, color_set="all"), palette=pal, catalog=cat)
    assert "Black" in set(p_all.grid.colors.ravel().tolist())
    assert "Black" not in set(p_rec.grid.colors.ravel().tolist())
