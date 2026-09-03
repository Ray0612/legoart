"""马赛克处理（采样 / 量化 / 大板合并 / 凸起分层）。

M1：sampling + quantize；merge_plates / relief 随 M2。
"""

from .quantize import quantize_grid
from .sampling import load_rgb_image, sample_grid

__all__ = ["load_rgb_image", "sample_grid", "quantize_grid"]
