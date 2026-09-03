"""拍照识别核心测试：opencv 分割候选 + 过滤 + 降级解析。"""

import numpy as np
import pytest
from PIL import Image

from legoart import api
from legoart.color import Palette
from legoart.detect import ColorSegDetector, PartCandidate, resolve_detector


@pytest.fixture(scope="module")
def det():
    cat = api.load_catalog()
    pal = Palette([c for c in cat.colors if not c.is_trans])
    return ColorSegDetector(pal, k=6, min_area_frac=0.002, max_bg_frac=0.5, max_delta=30)


def _make_img(blocks):
    im = Image.new("RGB", (300, 200), (175, 175, 175))
    for (x, y, w, h, rgb) in blocks:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                im.putpixel((xx, yy), rgb)
    return np.asarray(im, dtype=np.uint8)


def test_detects_red_and_blue_blocks(det):
    blocks = [
        (40, 60, 60, 60, (201, 26, 9)),   # Red 精确官方色
        (180, 90, 60, 60, (0, 85, 191)),  # Blue
    ]
    arr = _make_img(blocks)
    cands = det.predict(arr)
    assert len(cands) >= 2
    for (x, y, w, h, _), expect_id in zip(blocks, ("Red", "Blue"), strict=False):
        hit = [
            c for c in cands
            if x <= c.center[0] <= x + w and y <= c.center[1] <= y + h
            and c.palette_color_id == expect_id
        ]
        assert hit, f"{expect_id} 块未被识别为 {expect_id}：{cands[:3]}"
        assert hit[0].delta < 6.0  # 平均色 ≈ 官方色


def test_invariants(det):
    arr = _make_img([(50, 30, 40, 40, (201, 26, 9))])
    cands = det.predict(arr)
    h, w = arr.shape[:2]
    for c in cands:
        assert c.area > 0 and c.w > 0 and c.h > 0
        assert 0 <= c.x and c.x + c.w <= w and 0 <= c.y and c.y + c.h <= h
        assert c.delta <= 30


def test_uniform_full_frame_dropped_as_background(det):
    arr = np.full((100, 100, 3), (230, 30, 20), dtype=np.uint8)  # 全幅一色
    assert det.predict(arr) == []


def test_tiny_specks_filtered():
    cat = api.load_catalog()
    pal = Palette([c for c in cat.colors if not c.is_trans])
    det = ColorSegDetector(pal, k=4, min_area_frac=0.01, max_delta=30)
    im = Image.new("RGB", (100, 100), (170, 170, 170))
    for (xx, yy) in ((20, 20), (70, 70)):
        for dy in range(3):
            for dx in range(3):
                im.putpixel((xx + dx, yy + dy), (201, 26, 9))  # 9px < 100px 下限
    assert det.predict(np.asarray(im, dtype=np.uint8)) == []


def test_resolve_falls_back_to_seg(monkeypatch):
    monkeypatch.delenv("LEGOART_DETECTOR_MODEL", raising=False)
    det, used_ai = resolve_detector()
    assert used_ai is False
    assert det.kind == "opencv-seg"


def test_candidate_bbox_helper():
    c = PartCandidate(x=5, y=7, w=10, h=4, area=40, avg_rgb=(1, 2, 3), palette_color_id="Red", delta=1.0)
    assert c.center == (10, 9)
    assert c.bbox == (5, 7, 15, 11)
