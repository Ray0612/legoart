"""艺术海报风测试：子集选择 + pipeline poster 路径。"""

import numpy as np
import pytest
from PIL import Image

from legoart import api
from legoart.mosaic.posterize import choose_palette


@pytest.fixture(scope="module")
def pal():
    return api.build_palette(api.load_catalog())


def _flat(rgb, h=24, w=24):
    return np.tile(np.array(rgb, dtype=np.float64), (h, w, 1))


def test_choose_flat_red_contains_red(pal):
    cells = _flat((201, 26, 9))
    chosen, subset = choose_palette(cells, pal, k=8)
    assert len(chosen) == len(set(chosen)) == 8
    assert len(subset) == 8
    assert "Red" in chosen


def test_choose_deterministic(pal):
    rng = np.random.default_rng(0)
    cells = rng.random((40, 40, 3)) * 255.0
    a, _ = choose_palette(cells, pal, k=12)
    b, _ = choose_palette(cells, pal, k=12)
    assert a == b


def test_pipeline_poster_limits_colors():
    im = Image.new("RGB", (160, 160))
    px = im.load()
    for x in range(160):
        for y in range(160):
            px[x, y] = (int(255 * x / 160), int(120 * y / 160), 60)
    from legoart.model import ImageSpec

    spec = ImageSpec(grid_w=32, grid_h=32, style_mode="poster", palette_k=12, auto_tone=False)
    plan = api.generate_plan(im, spec)
    used = set(plan.grid.colors.ravel().tolist())
    assert len(used) <= 12
    chosen = plan.spec.params_extra.get("poster_palette", [])
    assert 0 < len(chosen) <= 12
    assert used <= set(chosen)


def test_pipeline_photo_default_unaffected():
    from legoart.model import ImageSpec

    im = Image.new("RGB", (64, 48), (30, 90, 160))
    spec = ImageSpec(grid_w=16, grid_h=16, auto_tone=False)
    plan = api.generate_plan(im, spec)
    assert plan.spec.params_extra.get("poster_palette") is None or "poster_palette" not in plan.spec.params_extra
