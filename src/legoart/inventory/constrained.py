"""库存约束求解（D7/D13）与替代规则（原文档 §8-2：2×1x2 → 1x4）。

实现细节：
- 需求 = 合并后的板件（每个 PartPlacement 一件）；
- 精确：design+color 都有库存 → 直接用；
- 近似替代（策略 A）候选顺序：同形同色(精确) > 同形最近色 > 可铺缩同色 > 可铺缩最近色；
- 可铺缩：库存板件尺寸 (pw,ph) 能整除需求 footprint (w,h)，k 片铺满（保持同层几何）；
- 缺件清单（策略 B）：只做精确匹配，缺的列 MissingList；
- 极限拼搭（策略 C）：只用库存精确匹配，未匹配格留空。
输出 SolverResult{placements, missing, substituted, allocations}——allocations 供
确认拼搭时扣减（含替代件，聚合为 (design,color,qty)）。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


from ..catalog import Catalog
from ..color import Palette
from ..color.ciede2000 import delta_e00
from ..model import BomItem, PartPlacement
from ..model.image_spec import ShortageStrategy

StockMap = dict[tuple[str, str], int]

_BIG = 400.0  # 未知颜色的距离哨兵


@dataclass(slots=True)
class SolverResult:
    placements: list[PartPlacement] = field(default_factory=list)
    missing: list[BomItem] = field(default_factory=list)
    substituted: list[tuple[PartPlacement, str, int, str]] = field(default_factory=list)  # (原需求, 替换design, 件数k, 替换color)
    allocations: list[tuple[str, str, int]] = field(default_factory=list)  # (design,color,qty) 扣减用
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.placements or self.missing or self.substituted)


def _lab_index(palette: Palette | None) -> dict[str, int]:
    if palette is None:
        return {}
    return {cid: i for i, cid in enumerate(palette.ids)}


def _color_dist(palette: Palette | None, idx: dict[str, int], a: str, b: str) -> float:
    if palette is None or a not in idx or b not in idx:
        return _BIG
    return float(delta_e00(palette.lab[idx[a]][None, :], palette.lab[idx[b]][None, :])[0])


def _plate_dims(catalog: Catalog, design_id: str) -> tuple[int, int] | None:
    p = catalog.part(design_id)
    if p is None or p.shape_family != "plate":
        return None
    return (p.stud_w, p.stud_h)


def _tile_options(fw: int, fh: int, dims: tuple[int, int]) -> list[tuple[int, int, int]]:
    """footprint 可被 dims(任意旋转) 整除 → 返回 [(orientation_w, orientation_h, k)]。"""
    pw, ph = dims
    out: list[tuple[int, int, int]] = []
    for ow, oh in ((pw, ph), (ph, pw)):
        if fw >= ow and fh >= oh and fw % ow == 0 and fh % oh == 0:
            out.append((ow, oh, (fw // ow) * (fh // oh)))
    return out


def _sub_placements(orig: PartPlacement, design_id: str, color_id: str, ow: int, oh: int, k: int) -> list[PartPlacement]:
    """把原板件 footprint 用 k 片 (ow×oh) 铺满，逐片生成新锚点（行主序）。"""
    out: list[PartPlacement] = []
    per_row = orig.w // ow
    for i in range(k):
        r, c = divmod(i, per_row)
        out.append(
            PartPlacement(
                design_id=design_id,
                color_id=color_id,
                layer=orig.layer,
                x=orig.x + c * ow,
                y=orig.y + r * oh,
                w=ow,
                h=oh,
            )
        )
    return out


class _StockBook:
    """求解中的可消费库存账本。"""

    def __init__(self, stock: StockMap) -> None:
        self._s: dict = {k: int(v) for k, v in stock.items()}

    def avail(self, design: str, color: str) -> int:
        return self._s.get((design, color), 0)

    def take(self, design: str, color: str, qty: int) -> None:
        self._s[(design, color)] = self._s.get((design, color), 0) - qty


def solve_inventory(
    placements: list[PartPlacement],
    stock: StockMap,
    *,
    strategy: ShortageStrategy,
    catalog: Catalog,
    palette: Palette | None = None,
    demanded_color: str | None = None,  # 预留（多需求共用时用）
) -> SolverResult:
    book = _StockBook(stock)
    idx = _lab_index(palette)
    result = SolverResult()
    missing_agg: dict[tuple[str, str], int] = defaultdict(int)

    for orig in placements:
        fw, fh = orig.w, orig.h
        exact = book.avail(orig.design_id, orig.color_id)

        if exact > 0:
            book.take(orig.design_id, orig.color_id, 1)
            result.placements.append(orig)
            continue

        if strategy == ShortageStrategy.MISSING_LIST:
            missing_agg[(orig.design_id, orig.color_id)] += 1
            continue
        if strategy == ShortageStrategy.EXTREME:
            missing_agg[(orig.design_id, orig.color_id)] += 1
            continue

        # APPROXIMATE：同形同色没有 → 找替代
        placed = False
        # L2: 同形其他颜色（按 ΔE00 最近）
        same_shape = [
            (d, c) for (d, c), v in book._s.items() if v > 0 and d == orig.design_id and c != orig.color_id
        ]
        if same_shape:
            same_shape.sort(key=lambda dc: _color_dist(palette, idx, orig.color_id, dc[1]))
            for d, c in same_shape:
                if book.avail(d, c) > 0:
                    book.take(d, c, 1)
                    result.placements.append(
                        PartPlacement(d, c, orig.layer, orig.x, orig.y, orig.w, orig.h)
                    )
                    result.substituted.append((orig, d, 1, c))
                    placed = True
                    break
        # L3/L4: 可铺缩的板件（先同色后最近色）
        if not placed:
            tiles: list[tuple[str, str, int, int, int, float]] = []  # design,color,ow,oh,k,dist
            for (d, c), v in book._s.items():
                if v <= 0 or d == orig.design_id:
                    continue
                dims = _plate_dims(catalog, d)
                if dims is None:
                    continue
                for ow, oh, k in _tile_options(fw, fh, dims):
                    if k <= 0 or v < k:
                        continue
                    tiles.append((d, c, ow, oh, k, _color_dist(palette, idx, orig.color_id, c)))
            # 先同色（dist=0 为同色情形已在上文排除 d!=orig.design 但颜色可等于 orig.color）
            # 排序：颜色差小优先；同色时片数 k 小优先（用更大片、更少拆分）
            tiles.sort(key=lambda t: (t[5], t[4]))
            for d, c, ow, oh, k, _ in tiles:
                if book.avail(d, c) >= k:
                    book.take(d, c, k)
                    result.placements.extend(_sub_placements(orig, d, c, ow, oh, k))
                    result.substituted.append((orig, d, k, c))
                    placed = True
                    break
        if not placed:
            missing_agg[(orig.design_id, orig.color_id)] += 1

    result.missing = [BomItem(d, c, q) for (d, c), q in sorted(missing_agg.items())]
    if result.missing and strategy == ShortageStrategy.EXTREME:
        result.warnings.append("极限拼搭：缺件位置已留空，可完成的拼搭以 placements 为准")
    if result.missing and strategy == ShortageStrategy.MISSING_LIST:
        result.warnings.append(
            "缺件清单已生成：保留原色方案，缺失件需另行购买（BrickLink 等）"
        )
    # 精确命中的件也计入扣减 allocation
    alloc_map: dict[tuple[str, str], int] = defaultdict(int)
    for p in result.placements:
        alloc_map[(p.design_id, p.color_id)] += 1
    # 与 substituted 去重：直接以 placements 聚合为准（substituted 仅展示用）
    result.allocations = [(d, c, q) for (d, c), q in sorted(alloc_map.items())]
    return result
