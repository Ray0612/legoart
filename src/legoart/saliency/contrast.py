"""内置离线显著性：Lab 局部对比度（无需权重）。

启发式：对图像做高斯模糊得到"背景估计"，ΔE00(原图, 背景) 大 = 视觉重点。
适合色彩鲜明的画作重点拾取；真 U²-Net 权重就绪后可替换（见 resolve/u2net）。
"""

from __future__ import annotations

import numpy as np

from ..color import convert

_BLUR_K = 9


class ContrastSaliency:
    kind = "contrast"

    def predict(self, rgb: np.ndarray) -> np.ndarray:
        arr = np.asarray(rgb, dtype=np.float64)
        lab = convert.rgb_to_lab(arr)

        # 全局色彩凸显：与整幅均值色差大 = "跳出画面"（实心区域内部也高）
        mean_lab = lab.reshape(-1, 3).mean(axis=0)
        gdist = np.sqrt(((lab - mean_lab) ** 2).sum(axis=-1))

        # 局部边缘：与高斯模糊背景的色差（细纹理/轮廓）
        try:
            import cv2

            blurred = cv2.GaussianBlur(lab, (_BLUR_K, _BLUR_K), 0)
        except ImportError:  # 无 opencv 兜底：整幅均值
            blurred = np.broadcast_to(mean_lab, lab.shape).copy()
        ldiff = lab - blurred
        ldist = np.sqrt((ldiff[..., 0] ** 2) + (ldiff[..., 1] ** 2) + (ldiff[..., 2] ** 2))

        def _norm(d):
            lo, hi = float(d.min()), float(d.max())
            if hi - lo < 1e-9:
                return None
            return (d - lo) / (hi - lo)

        gn, ln = _norm(gdist), _norm(ldist)
        if gn is None:
            return np.zeros_like(gdist)
        score = np.maximum(gn, ln if ln is not None else 0.0)
        return score
