"""端到端编排：图片 → MosaicPlan（技术方案 §4 数据流）。

M2 覆盖：采样 → CIEDE2000 量化 → （可选）显著性凸起 → 分层 → 同色大板合并
→ 按层 BOM。M1 的"1×1 占位 BOM"已被真实合并件替换。
库存约束求解（需求轴）在 M4 接入；纹理风格在第二迭代。
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image

from .color import Palette
from .errors import DataError, LegoArtTimeoutError, NotSupportedError
from .model import BomItem, BomModel, GridModel, ImageSpec, LayerStack, MosaicPlan, Region, RegionSet
from .model.image_spec import StyleKind
from .mosaic import merge_grid, quantize_grid, sample_grid, load_rgb_image
from .mosaic.relief import build_layer_stack

ProgressFn = Callable[[str, float], None]  # (stage, 0..1)


def _report(progress: ProgressFn | None, stage: str, frac: float) -> None:
    if progress is not None:
        try:
            progress(stage, min(max(frac, 0.0), 1.0))
        except Exception:
            pass  # 进度回调异常不阻断生成


def _warn_residual(deltas) -> list[str]:
    mean = float(np.mean(deltas))
    p95 = float(np.percentile(deltas, 95))
    if mean > 4.0 or p95 > 8.0:
        return [
            f"CIEDE2000 residual high (mean {mean:.2f}, p95 {p95:.2f}); "
            "consider a larger grid or another palette set"
        ]
    return []


def _detect_regions(im: Image.Image, grid_h: int, grid_w: int, warnings: list[str]) -> list[Region]:
    """显著性 → 凸起区域（网格分辨率）。模型缺失时降级内置对比度并提示。"""
    from .saliency import extract_regions, resolve_provider

    provider, used_ai = resolve_provider()
    if not used_ai:
        warnings.append(
            "saliency: AI model missing, using built-in contrast saliency "
            "(see scripts/fetch_models.py)"
        )
    # 显著性在 ≤1024 宽的源图上算，再缩放到网格分辨率
    scale = min(1.0, 1024.0 / im.width)
    sw, sh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    arr = np.asarray(im.resize((sw, sh)), dtype=np.float64)
    score = provider.predict(arr)  # (sh, sw) 0..1
    if score.shape != (sh, sw):
        try:
            import cv2

            score = cv2.resize(score, (sw, sh), interpolation=cv2.INTER_LINEAR)
        except ImportError:
            pass
    # 缩到网格
    try:
        import cv2

        score_grid = cv2.resize(score, (grid_w, grid_h), interpolation=cv2.INTER_AREA)
    except ImportError:
        from numpy import interp  # noqa: F401  # 兜底（不常用）

        score_grid = np.zeros((grid_h, grid_w), dtype=np.float64)
    return extract_regions(score_grid)


def generate_plan(
    image,
    spec: ImageSpec,
    *,
    palette: Palette | None = None,
    catalog=None,
    plates=None,
    regions: list[Region] | None = None,
    progress: ProgressFn | None = None,
    budget_ms: int = 60_000,
) -> MosaicPlan:
    """执行一次方案生成（忽略库存）。

    ``image``: PIL Image / 路径 / 文件对象。
    ``regions``: 显式凸起区域（跳过显著性检测，测试/用户微调用）。
    ``plates``: 板型白名单（PartSpec 列表）；默认取 catalog 的 plate 系列。
    """
    t0 = time.perf_counter()
    started = time.monotonic()

    def _budget():
        if (time.monotonic() - started) * 1000 > budget_ms:
            raise LegoArtTimeoutError(
                f"本地计算超过 {budget_ms / 1000:.0f}s 预算", code="ERR_OVER_60S"
            )

    if spec.style != StyleKind.COLOR_BLOCK:
        raise NotSupportedError("纹理保留风格将在第二迭代实现")

    if isinstance(image, (str, Path)):
        im = load_rgb_image(image)
    elif isinstance(image, Image.Image):
        im = image.convert("RGB")
    elif hasattr(image, "read"):  # 文件对象 / BytesIO（GUI 线程内图片传递）
        im = load_rgb_image(image)
    else:
        raise DataError(f"不支持的图片输入类型: {type(image).__name__}")

    if plates is None:
        if catalog is None:
            raise DataError("缺少板型白名单：请经 api.generate_plan 或传入 plates")
        plates = catalog.plate_candidates()

    w = spec.grid_w
    if w < 1:
        raise DataError(f"网格宽非法: {w}（studs ≥ 1）")
    h = spec.grid_h
    if h <= 0:
        aspect = im.width / max(im.height, 1)
        h = max(1, round(w / aspect))

    _report(progress, "sample", 0.05)
    cells = sample_grid(im, w, h)
    _budget()

    pal = palette
    if pal is None:
        from .api import build_palette, load_catalog

        pal = build_palette(catalog or load_catalog())
    color_set = spec.color_set if spec.color_set in ("recommended", "all") else "recommended"

    _report(progress, "quantize", 0.4)
    grid, deltas = quantize_grid(cells, pal, color_set=color_set)
    _budget()

    warnings = _warn_residual(deltas)

    # 凸起区域：显式注入 > AI/内置显著性
    region_list: list[Region] = []
    if regions is not None:
        region_list = list(regions)
    elif spec.saliency_enabled:
        try:
            region_list = _detect_regions(im, grid.height, grid.width, warnings)
            # 用户设置的层高上限只约束 AI 切出的区域（显式注入的区域是用户意图）
            cap = max(1, int(getattr(spec, "saliency_max_raise", 3)))
            for r in region_list:
                r.raise_layers = min(max(r.raise_layers, 1), cap)
        except Exception as e:  # 显著性失败不阻断主流程
            warnings.append(f"saliency detection skipped: {e}")
        _budget()

    _report(progress, "relief", 0.6)
    stack = build_layer_stack(grid, region_list)

    _report(progress, "merge", 0.75)
    placements = []
    for layer in stack.layers:
        placements.extend(merge_grid(layer.grid, plates, layer=layer.level))
    _budget()

    # BOM：按 (层, 设计号, 颜色) 汇总（单层用量）；totals() 出跨层合计
    bom = BomModel()
    counts: Counter = Counter()
    for p in placements:
        counts[(p.layer, p.design_id, p.color_id)] += 1
    for (lvl, design_id, color_id), qty in sorted(counts.items()):
        bom.add(design_id, color_id, int(qty), layer=lvl)

    _report(progress, "assemble", 0.95)
    plan = MosaicPlan(
        spec=spec,
        grid=grid,
        regions=RegionSet(region_list),
        stack=stack,
        placements=placements,
        bom=bom,
        warnings=warnings,
        elapsed_ms=int((time.perf_counter() - t0) * 1000),
    )
    _report(progress, "done", 1.0)
    return plan
