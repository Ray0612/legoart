"""sRGB <-> Lab 转换测试（公开锚点值 + 往返一致）。"""

import numpy as np
import pytest

from legoart.color.convert import lab_to_rgb, rgb_to_lab


def _assert_close(actual: np.ndarray, expected: tuple[float, float, float], tol: float = 0.25):
    np.testing.assert_allclose(actual, expected, atol=tol)


@pytest.mark.parametrize(
    "rgb,lab",
    [
        ((255, 255, 255), (100.0, 0.0, 0.0)),          # 白
        ((0, 0, 0), (0.0, 0.0, 0.0)),                  # 黑
        ((255, 0, 0), (53.24, 80.09, 67.20)),          # 纯红 (D65 标准值)
        ((0, 255, 0), (87.73, -86.18, 83.18)),         # 纯绿
        ((0, 0, 255), (32.30, 79.19, -107.86)),        # 纯蓝
    ],
)
def test_rgb_to_lab_anchors(rgb, lab):
    _assert_close(rgb_to_lab(np.array([rgb], dtype=np.float64))[0], lab, tol=0.3)


def test_roundtrip_samples():
    rng = np.random.default_rng(42)
    samples = rng.integers(0, 256, size=(20, 3))
    back = lab_to_rgb(rgb_to_lab(samples))
    # 允许一定色域误差
    np.testing.assert_allclose(back, samples, atol=2.0)


def test_roundtrip_white_exact():
    lab = rgb_to_lab(np.array([[255.0, 255.0, 255.0]]))
    back = lab_to_rgb(lab)
    np.testing.assert_allclose(back, [[255.0, 255.0, 255.0]], atol=0.6)


def test_shapes():
    rng = np.random.default_rng(7)
    x = rng.random((4, 5, 3)) * 255
    lab = rgb_to_lab(x)
    assert lab.shape == (4, 5, 3)
    assert rgb_to_lab(np.zeros((3,), dtype=np.float64)).shape == (3,)
