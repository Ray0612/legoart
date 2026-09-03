"""端到端编排：图片 → MosaicPlan（技术方案 §4 数据流，M1 覆盖 采样→量化→网格/BOM）。

M1 口径：
- 风格仅 COLOR_BLOCK（纹理二期）；
- 输出单层 LayerStack（level 0）+ 按"每格=1×1 板"的 BOM 汇总
  （同色大板合并 M2 将替换 placements/BOM 明细）；
- 凸起/库存求解 M2/M4 接入；本模块预留进度回调与耗时预算。
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from .color import Palette
from .errors import DataError, LegoArtTimeoutError, NotSupportedError
from .model import BomModel, GridModel, ImageSpec, LayerStack, MosaicPlan
from .model.image_spec import StyleKind
from .mosaic.quantize import quantize_grid
from .mosaic.sampling import load_rgb_image, sample_grid

ProgressFn = Callable[[str, float], None]  # (stage, 0..1)

_STAGES = ("sample", "quantize", "assemble")

_PLATE_1x1 = "3024"  # BOM 占位零件（M2 合并后替换）


def _make_palette() -> Palette:
    from .api import build_palette  # 函数级导入避免模块环

    return build_palette()


def _warn_residual(deltas) -> list[str]:
    import numpy as np

    mean = float(np.mean(deltas))
    p95 = float(np.percentile(deltas, 95))
    warnings = []
    if mean > 4.0 or p95 > 8.0:
        warnings.append(
            f"CIEDE2000 residual high (mean {mean:.2f}, p95 {p95:.2f}); "
            "consider a larger grid or another palette set"
        )
    return warnings


def generate_plan(
    image,
    spec: ImageSpec,
    *,
    palette: Palette | None = None,
    catalog=None,
    progress: ProgressFn | None = None,
    budget_ms: int = 60_000,
) -> MosaicPlan:
    """执行一次方案生成（忽略库存）。

    ``image`` 可为 PIL Image / 路径 / 文件对象；``spec.grid_h<=0`` 时按图片
    宽高比自动补全（D4），结果存回网格实际尺寸。
    """
    t0 = time.perf_counter()
    started = time.monotonic()

    def _budget():
        if (time.monotonic() - started) * 1000 > budget_ms:
            raise LegoArtTimeoutError(
                f"本地计算超过 {budget_ms / 1000:.0f}s 预算", code="ERR_OVER_60S"
            )

    def _report(stage: str, frac: float) -> None:
        if progress is not None:
            try:
                progress(stage, min(max(frac, 0.0), 1.0))
            except Exception:
                pass  # 进度回调异常不阻断生成

    if spec.style != StyleKind.COLOR_BLOCK:
        raise NotSupportedError("纹理保留风格将在第二迭代实现")

    if isinstance(image, (str, Path, bytes)):
        im = load_rgb_image(image)
    elif isinstance(image, Image.Image):
        im = image.convert("RGB")
    else:
        raise DataError(f"不支持的图片输入类型: {type(image).__name__}")

    w = spec.grid_w
    if w < 1:
        raise DataError(f"网格宽非法: {w}（studs ≥ 1）")

    h = spec.grid_h
    if h <= 0:
        aspect = im.width / max(im.height, 1)
        h = max(1, round(w / aspect))
    if h < 1:
        raise DataError(f"网格高非法: {h}")

    _report("sample", 0.05)
    cells = sample_grid(im, w, h)
    _budget()

    pal = palette or _make_palette()
    color_set = spec.color_set if spec.color_set in ("recommended", "all") else "recommended"

    _report("quantize", 0.45)
    grid, deltas = quantize_grid(cells, pal, color_set=color_set)
    _budget()

    # 单层结构 + 1×1 板占位 BOM（M2 大板合并替换）
    stack = LayerStack(width=grid.width, height=grid.height)
    stack.add(0, grid)

    bom = BomModel()
    counts: Counter[str] = Counter()
    for row in grid.colors.tolist():
        for cid in row:
            counts[cid] += 1
    for cid, n in counts.items():
        if catalog is not None and catalog.part(_PLATE_1x1) is None:
            raise DataError("目录缺少 1×1 板(3024)，无法生成占位 BOM", code="ERR_CATALOG")
        bom.add(_PLATE_1x1, cid, int(n), layer=0)

    _report("assemble", 0.9)
    plan = MosaicPlan(
        spec=spec,
        grid=grid,
        stack=stack,
        bom=bom,
        warnings=_warn_residual(deltas),
        elapsed_ms=int((time.perf_counter() - t0) * 1000),
    )
    _report("done", 1.0)
    return plan
