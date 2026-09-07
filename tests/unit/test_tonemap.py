"""auto_tone 测试：暗图提升命中率；纯色图跳过不改变。"""

import numpy as np

from legoart import api
from legoart.mosaic import quantize_grid, sample_grid
from legoart.mosaic.tonemap import auto_tone


def _pal():
    return api.build_palette(api.load_catalog())


def _dark_gradient(h=48, w=48):
    """暗部重的渐变（模拟"彩色图暗部重"）：上暗下微亮。"""
    rows = []
    for y in range(h):
        f = y / h
        base = np.array([28 + 90 * f, 40 + 100 * f, 18 + 70 * f])  # 黄绿橄榄轴
        rows.append(np.tile(base, (w, 1)))
    return np.stack(rows)


def test_dark_image_tone_improves_match():
    pal = _pal()
    cells = _dark_gradient()
    # 直接看亮度：默认太暗（median L 明显低于调色板中位）
    before = cells
    after = auto_tone(cells, pal)
    from legoart.color.convert import rgb_to_lab

    assert rgb_to_lab(after)[..., 0].mean() > rgb_to_lab(before)[..., 0].mean() + 3

    g0, de0 = quantize_grid(before, pal, color_set="recommended")
    g1, de1 = quantize_grid(after, pal, color_set="recommended")
    assert de1.mean() < de0.mean() * 0.9
    assert (de1 > 12).mean() < (de0 > 12).mean()


def test_flat_color_untouched():
    pal = _pal()
    cells = np.full((16, 16, 3), (150.0, 40.0, 40.0))
    out = auto_tone(cells, pal)
    np.testing.assert_allclose(out, cells)


def test_real_sample_metrics_via_pipeline():
    """用用户样例图(1 209).jpg 做回归：自动调色后 mean ΔE 应明显低于关闭。"""
    import os

    p = r"tmp/1 (209).jpg"
    if not os.path.exists(p):
        import pytest

        pytest.skip("用户样例图不在")
    from PIL import Image

    from legoart import api
    from legoart.model import ImageSpec

    im = Image.open(p).convert("RGB")
    spec_off = ImageSpec(grid_w=48, grid_h=0, auto_tone=False)
    spec_on = ImageSpec(grid_w=48, grid_h=0, auto_tone=True)
    # 直接比较量化残差（pipeline 内部已量化；此处重算）
    pal = api.build_palette(api.load_catalog())
    W = 48
    H = max(1, round(W * im.height / im.width))
    cells = sample_grid(im, W, H)
    cells_on = auto_tone(cells, pal)
    _, de0 = quantize_grid(cells, pal, color_set="recommended")
    _, de1 = quantize_grid(cells_on, pal, color_set="recommended")
    assert de1.mean() < de0.mean() - 1.5
    assert (de1 > 12).mean() < (de0 > 12).mean()
