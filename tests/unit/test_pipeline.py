"""Pipeline 端到端测试（M1：采样→量化→单层网格+BOM）。"""

import numpy as np
import pytest
from PIL import Image

from legoart import api
from legoart.errors import DataError, NotSupportedError
from legoart.model import ImageSpec, MosaicPlan
from legoart.model.image_spec import StyleKind


def _gradient_image(w=320, h=160):
    """横向红→蓝渐变 + 底部白条，便于量化产生多色。"""
    im = Image.new("RGB", (w, h))
    px = im.load()
    for x in range(w):
        r = int(255 * (1 - x / w))
        b = int(255 * x / w)
        for y in range(h):
            if y > int(h * 0.75):
                px[x, y] = (255, 255, 255)
            else:
                px[x, y] = (r, 0, b)
    return im


def _spec(w=48, h=24, **kw):
    return ImageSpec(grid_w=w, grid_h=h, style=StyleKind.COLOR_BLOCK, **kw)


def test_generate_full_plan():
    plan = api.generate_plan(_gradient_image(), _spec())
    assert isinstance(plan, MosaicPlan)
    assert plan.grid.width == 48 and plan.grid.height == 24
    assert plan.stack is not None and plan.stack.height_total == 1
    # BOM 占位：每格一片 1×1，总用量 = 格数
    total = sum(i.qty for i in plan.bom.items)
    assert total == 48 * 24
    assert plan.elapsed_ms >= 0
    assert all("3024" == i.design_id for i in plan.bom.items)


def test_multi_color_usage():
    plan = api.generate_plan(_gradient_image(), _spec())
    colors = set(plan.grid.colors.ravel().tolist())
    assert len(colors) >= 2


def test_auto_height_from_aspect():
    spec = ImageSpec(grid_w=20, grid_h=0)  # 2:1 图 → h=10
    plan = api.generate_plan(_gradient_image(400, 200), spec)
    assert plan.grid.height == 10


def test_style_not_supported_yet():
    spec = ImageSpec(grid_w=8, grid_h=8, style=StyleKind.TEXTURE)
    with pytest.raises(NotSupportedError):
        api.generate_plan(_gradient_image(32, 32), spec)


def test_bad_width():
    with pytest.raises(DataError):
        api.generate_plan(_gradient_image(), _spec(w=0))


def test_snapshot_json_roundtrip_fields(tmp_path):
    plan = api.generate_plan(_gradient_image(), _spec())
    d = plan.to_dict()
    out = tmp_path / "plan.json"
    import json

    out.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["grid"]["w"] == 48
    assert len(loaded["stack"]) == 1
    assert loaded["bom"], "BOM 非空"
    assert loaded["spec"]["style"] == "color_block"


def test_progress_called():
    stages = []
    api.generate_plan(_gradient_image(), _spec(8, 8), progress=lambda s, f: stages.append(s))
    assert "sample" in stages and "quantize" in stages and "done" in stages


def test_color_set_all_uses_more_colors_than_recommended():
    from legoart.catalog.models import ColorSpec
    from legoart.color import Palette

    # 注入含“非推荐色 Black”的调色板，验证 color_set 过滤
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
