"""CIEDE2000 测试：Sharma et al. 2005 公开锚点 + 性质测试。"""

import numpy as np
import pytest

from legoart.color.ciede2000 import delta_e00, delta_e00_pairwise

# 经典锚点（Sharma 论文 Table 1 子集），容差 1e-3
ANCHORS = [
    ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
    ((50.0, 0.0, 0.0), (50.0, -1.0, 2.0), 2.3669),
    ((50.0, 2.4900, -0.0010), (50.0, -2.4900, 0.0009), 7.1792),
    ((50.0, 2.5, 0.0), (73.0, 25.0, -18.0), 27.1492),
    ((50.0, 2.5, 0.0), (50.0, 3.1736, 0.5854), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
]


@pytest.mark.parametrize("lab1,lab2,expected", ANCHORS)
def test_anchors(lab1, lab2, expected):
    a = np.array([lab1], dtype=np.float64)
    b = np.array([lab2], dtype=np.float64)
    np.testing.assert_allclose(delta_e00(a, b)[0], expected, atol=1e-3)


def test_identical_zero():
    lab = np.array([[50.0, 2.5, 0.0], [30.0, -10.0, 20.0]])
    np.testing.assert_array_almost_equal(delta_e00(lab, lab), [0.0, 0.0], decimal=12)


def test_symmetric():
    a = np.array([[50.0, 2.49, -0.001], [20.0, 12.0, -30.0]])
    b = np.array([[50.0, -2.49, 0.0009], [35.0, -5.0, 44.0]])
    np.testing.assert_allclose(delta_e00(a, b), delta_e00(b, a), atol=1e-9)


def test_pairwise_matches_elementwise():
    a = np.array([[50.0, 2.49, -0.001], [20.0, 12.0, -30.0], [10.0, 0.0, 0.0]])
    b = np.array([[50.0, -2.49, 0.0009], [35.0, -5.0, 44.0]])
    pw = delta_e00_pairwise(a, b)
    assert pw.shape == (3, 2)
    for i in range(3):
        for j in range(2):
            expected = delta_e00(a[i][None, :], b[j][None, :])[0]
            np.testing.assert_allclose(pw[i, j], expected, atol=1e-9)


def test_gray_neutral_edge():
    # 无彩度样本不应崩溃，且结果有界（亮度差受 Sl 加权，非纯 ΔL）
    a = np.array([[50.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    b = np.array([[55.0, 0.0, 0.0], [12.0, 0.0, 0.0]])
    out = delta_e00(a, b)
    assert np.all(np.isfinite(out))
    lbar = 52.5
    sl = 1.0 + 0.015 * (lbar - 50.0) ** 2 / np.sqrt(20.0 + (lbar - 50.0) ** 2)
    np.testing.assert_allclose(out[0], 5.0 / sl, atol=1e-6)
