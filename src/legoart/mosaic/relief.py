"""凸起 → 分层结构（D6/D9，纯 numpy，无模型依赖）。

规则：
- level 0 = 底层整幅色格；
- 区域 r 若 raise_layers=N，则 level 1..N 只在该区域 footprint 铺砖，
  顶面/叠层颜色 = 该格在 level 0 的颜色（"垫高多层板"语义，侧视可见同色）；
- 区域可重叠：更高层的格子取最后写入（区域按 raise 降序处理）。
"""

from __future__ import annotations

import numpy as np

from ..errors import DataError
from ..model import GridModel, LayerStack, Region
from .merge_plates import _EMPTY


def build_layer_stack(base: GridModel, regions: list[Region]) -> LayerStack:
    """由底网格 + 凸起区域构建物理分层。"""
    h, w = base.height, base.width
    for r in regions:
        if r.mask.shape != (h, w):
            raise DataError(f"凸起区域 mask {r.mask.shape} 与网格 {h}x{w} 不一致")
        if r.raise_layers < 1:
            raise DataError(f"raise_layers 必须 ≥ 1，got {r.raise_layers}")
    if not regions:
        stack = LayerStack(width=w, height=h)
        stack.add(0, base)
        return stack

    max_raise = max((r.raise_layers for r in regions), default=0)

    # level 0 用底网格；更高层先置空，再按区域写入
    layers: dict[int, np.ndarray] = {0: base.colors.copy()}
    for lvl in range(1, max_raise + 1):
        arr = np.full((h, w), _EMPTY, dtype=object)
        # raise 高的区域先写，重叠处以先写者为准（视觉上层在下，仅学术约定，简化）
        for r in sorted(regions, key=lambda r: -r.raise_layers):
            if r.raise_layers >= lvl:
                arr[r.mask] = base.colors[r.mask]
        layers[lvl] = arr

    stack = LayerStack(width=w, height=h)
    for lvl in range(max_raise + 1):
        stack.add(lvl, GridModel(width=w, height=h, colors=layers[lvl]))
    return stack
