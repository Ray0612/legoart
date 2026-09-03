"""采样测试：面积平均 / 中值降噪 / 图片加载错误。"""

import numpy as np
import pytest
from PIL import Image

from legoart.errors import DataError
from legoart.mosaic.sampling import load_rgb_image, sample_grid


def _img_from_blocks(blocks, block=16):
    """把 (bh, bw, 3) 色块拼成图片：每块放大为 block×block。"""
    bh, bw = blocks.shape[:2]
    im = Image.new("RGB", (bw * block, bh * block))
    px = im.load()
    for y in range(bh):
        for x in range(bw):
            rgb = tuple(int(v) for v in blocks[y, x])
            for dy in range(block):
                for dx in range(block):
                    px[x * block + dx, y * block + dy] = rgb
    return im


def test_area_average_two_blocks():
    blocks = np.array(
        [
            [[255.0, 0.0, 0.0], [0.0, 0.0, 255.0]],
            [[0.0, 255.0, 0.0], [255.0, 255.0, 255.0]],
        ]
    )
    im = _img_from_blocks(blocks)
    cells = sample_grid(im, 2, 2, median_ksize=0)
    np.testing.assert_allclose(cells, blocks, atol=1.0)


def test_downsample_average_halves_mixed():
    # 8x8 全红 + 2x8 全白横向拼 → 10 宽按 BOX 缩到 5 格：前 4 格纯红、末格纯白
    im = Image.new("RGB", (10, 4))
    im.paste((255, 0, 0), (0, 0, 8, 4))
    im.paste((255, 255, 255), (8, 0, 10, 4))
    cells = sample_grid(im, 5, 2, median_ksize=0)
    assert cells[0, 0, 1] < 1.0  # 红格绿分量≈0
    assert cells[0, 0, 2] < 1.0
    assert cells[0, 4, 1] > 254.0  # 白格
    assert cells[0, 4, 2] > 254.0


def test_median_denoise_removes_salt():
    im = Image.new("RGB", (5, 5), (100, 100, 100))
    im.putpixel((2, 2), (200, 200, 200))
    with_noise = sample_grid(im, 5, 5, median_ksize=0)
    assert with_noise[2, 2, 0] > 150
    cleaned = sample_grid(im, 5, 5, median_ksize=3)
    assert cleaned[2, 2, 0] == pytest.approx(100, abs=1.0)


def test_bad_dims():
    im = Image.new("RGB", (10, 10))
    with pytest.raises(DataError):
        sample_grid(im, 0, 10)
    with pytest.raises(DataError):
        sample_grid(im, 10, -1)
    with pytest.raises(DataError):
        sample_grid(im, 5000, 10)


def test_load_missing_file():
    with pytest.raises(DataError):
        load_rgb_image("no-such-file-xyz.png")


def test_load_and_convert_mode(tmp_path):
    p = tmp_path / "gray.png"
    Image.new("L", (4, 4), 128).save(p)
    im = load_rgb_image(p)
    assert im.mode == "RGB"
