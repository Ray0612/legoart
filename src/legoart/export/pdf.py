"""PDF 分层说明书（ReportLab 矢量）。

结构：封面（成品预览 + 参数）→ 物料清单 → （缺件/替代明细）→ 逐层：每层 6 视角
（俯/仰/正/背/左/右，矢量色格）。中文优先使用系统字体，缺失自动回退。
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

from ..catalog import Catalog
from ..color import Palette
from ..model import MosaicPlan

from .fonts import cn_font
from .views6 import bottom_grid, overview_grid, side_grid, top_grid

_EMPTY = (232, 232, 235)
_MISS = (40, 40, 45)


class GridFlowable(Flowable):
    """把 color_id 二维表渲染成矢量色格（'' = 空）。"""

    def __init__(self, grid: list[list[str]], palette: Palette | None, *, box_w: float, box_h: float):
        super().__init__()
        self.grid = grid
        self.palette = palette
        self.box_w = box_w
        self.box_h = box_h
        self.cell = 1.0

    def wrap(self, availWidth, availHeight):
        rows, cols = len(self.grid), len(self.grid[0]) if self.grid else 0
        if rows == 0 or cols == 0:
            self.width, self.height = 0, 0
            return 0, 0
        self.cell = max(0.6, min(availWidth / cols, availHeight / rows, self.box_w / cols, self.box_h / rows))
        self.width = self.cell * cols
        self.height = self.cell * rows
        return self.width, self.height

    def draw(self):
        if self.palette is None:
            return
        for y, row in enumerate(self.grid):
            for x, cid in enumerate(row):
                x0, y0 = x * self.cell, (len(self.grid) - 1 - y) * self.cell
                rgb = (255, 255, 255) if not cid else (self.palette.rgb_of(cid) or _MISS)
                self.canv.setFillColorRGB(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
                self.canv.rect(x0, y0, self.cell, self.cell, stroke=0, fill=1)
        self.canv.setStrokeColorRGB(0.6, 0.6, 0.6)
        self.canv.setLineWidth(0.25)
        self.canv.rect(0, 0, self.width, self.height, stroke=1, fill=0)


def _rgb(palette: Palette | None, color_id: str) -> tuple[int, int, int]:
    if palette:
        rgb = palette.rgb_of(color_id)
        if rgb:
            return rgb
    return (160, 160, 160)


def _palette_rgb(palette, color_id) -> str:
    r, g, b = _rgb(palette, color_id)
    return f"#{r:02X}{g:02X}{b:02X}"


def build_pdf(
    path: str | Path,
    plan: MosaicPlan,
    palette: Palette,
    catalog: Catalog | None = None,
    solver=None,
    *,
    lang: str = "zh",
) -> Path:
    from ..api import load_catalog

    cat = catalog or load_catalog()
    font = cn_font()
    spec = plan.spec
    stack = plan.stack
    levels = sorted(stack.layers, key=lambda x: x.level) if stack else []

    st_title = ParagraphStyle("t", fontName=font, fontSize=20, leading=26)
    st_h2 = ParagraphStyle("h2", fontName=font, fontSize=13, leading=18, spaceBefore=6)
    st_body = ParagraphStyle("b", fontName=font, fontSize=8.5, leading=12)
    st_cap = ParagraphStyle("cap", fontName=font, fontSize=8, leading=10, alignment=1)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out), pagesize=A4, leftMargin=1.4 * cm, rightMargin=1.4 * cm,
        topMargin=1.4 * cm, bottomMargin=1.6 * cm,
    )

    def _footer(canv, doc_):
        canv.saveState()
        canv.setFont(font, 8)
        canv.drawCentredString(A4[0] / 2, 0.7 * cm, f"第 {canv.getPageNumber()} 页")
        canv.restoreState()

    story: list = []

    # ---- 封面 ----
    story.append(Paragraph("乐高画作智能转换器 — 拼搭说明书", st_title))
    story.append(Spacer(1, 4))
    info_lines = [
        f"成品网格：{plan.grid.width} × {plan.grid.height} studs"
        f"（{plan.grid.width * plan.grid.height} 格）",
        f"风格：色块化 ｜ 需求轴：{'库存约束' if spec.use_inventory else '理想购物车'}"
        f" ｜ 候选色集：{spec.color_set}",
        f"物理层数：{plan.stack.height_total if plan.stack else 1}"
        f" ｜ 合并后板件 {len(plan.placements)} 片"
        f" ｜ 颜色 {len(set(plan.grid.colors.ravel().tolist()))} 种",
        f"目录版本 {spec.catalog_version or '-'} ｜ 生成 {plan.generated_at}"
        f" ｜ 计算耗时 {plan.elapsed_ms} ms",
    ]
    story.append(Paragraph("<br/>".join(info_lines), st_body))
    story.append(Spacer(1, 8))
    overview = GridFlowable(overview_grid(stack), palette, box_w=16.5 * cm, box_h=16.5 * cm)
    story.append(Paragraph("成品俯视预览", st_cap))
    story.append(Spacer(1, 2))
    story.append(overview)
    story.append(PageBreak())

    # ---- 物料清单 ----
    story.append(Paragraph("物料清单", st_h2))
    totals: dict[tuple[str, str], int] = {}
    per_layer: dict[tuple[str, str], dict[int, int]] = {}
    for item in plan.bom.items:
        key = (item.design_id, item.color_id)
        totals[key] = totals.get(key, 0) + item.qty
        if item.layer is not None:
            per_layer.setdefault(key, {})[item.layer] = per_layer.get(key, {}).get(item.layer, 0) + item.qty
    level_cols = [f"L{l.level}" for l in levels]
    head = ["设计号", "零件", "颜色", "RGB"] + level_cols + ["总用量"]
    body_rows = [head]
    for (design_id, color_id) in sorted(totals):
        part = cat.part(design_id)
        col = cat.color(color_id)
        line = [
            design_id,
            (part.name if part else design_id),
            (col.name_bl if col else color_id),
            _palette_rgb(palette, color_id),
        ]
        line += [per_layer.get((design_id, color_id), {}).get(l.level, 0) for l in levels]
        line.append(totals[(design_id, color_id)])
        body_rows.append(line)
    n_cols = len(head)
    bom_tbl = Table(body_rows, repeatRows=1)
    bom_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8ec")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(bom_tbl)
    story.append(Spacer(1, 6))

    if solver is not None:
        missing = list(getattr(solver, "missing", []))
        substituted = list(getattr(solver, "substituted", []))
        if missing:
            story.append(Paragraph("缺件清单（需另行购买）", st_h2))
            rows = [["设计号", "颜色", "数量"]] + [[m.design_id, m.color_id, m.qty] for m in missing]
            t = Table(rows)
            t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc"))]))
            story.append(t)
        if substituted:
            story.append(Paragraph("替代明细（近似策略）", st_h2))
            rows = [["原件", "原色", "→ 替换件", "替换色", "每处片数"]] + [
                [s[0].design_id, s[0].color_id, s[1], s[3], s[2]] for s in substituted
            ]
            t = Table(rows)
            t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc"))]))
            story.append(t)
        story.append(PageBreak())

    # ---- 逐层 6 视图 ----
    for lv in levels:
        block: list = []
        block.append(Paragraph(f"物理层 {lv.level}（自下而上第 {lv.level + 1} 层）", st_h2))
        top = top_grid(stack, lv.level)
        top_rows = [list(row) for row in top.colors.tolist()]
        block.append(Paragraph("俯视 —— 本层图案（新增面）", st_cap))
        block.append(GridFlowable(top_rows, palette, box_w=16.5 * cm, box_h=6 * cm))
        block.append(Spacer(1, 6))

        sub_rows: list[list] = []
        # 仰视(底面参考) + 正视
        bottom = bottom_grid(stack)
        bottom_rows = [list(r) for r in bottom]
        for cap, grid, box_w in (
            ("仰视（底面参考，各层不变）", bottom_rows, 7.5 * cm),
            ("正视", side_grid(stack, lv.level, "front"), 7.5 * cm),
        ):
            cell = [Paragraph(cap, st_cap)]
            cell.append(GridFlowable(grid, palette, box_w=box_w, box_h=2.6 * cm))
            sub_rows.append(cell)
        tbl = Table([sub_rows])
        tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        block.append(tbl)
        block.append(Spacer(1, 2))

        sub_rows2: list[list] = []
        for cap, grid in (
            ("背视", side_grid(stack, lv.level, "back")),
            ("左视", side_grid(stack, lv.level, "left")),
            ("右视", side_grid(stack, lv.level, "right")),
        ):
            cell = [Paragraph(cap, st_cap), GridFlowable(grid, palette, box_w=5.3 * cm, box_h=2.0 * cm)]
            sub_rows2.append(cell)
        tbl2 = Table([sub_rows2])
        tbl2.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        block.append(tbl2)
        # 本层零件
        layer_items = sorted(
            [i for i in plan.bom.items if i.layer == lv.level],
            key=lambda i: (i.design_id, i.color_id),
        )
        if layer_items:
            txt = "本层新增零件：" + "、".join(
                f"{i.design_id} {i.color_id} ×{i.qty}" for i in layer_items[:10]
            ) + ("…" if len(layer_items) > 10 else "")
            block.append(Paragraph(txt, st_body))
        story.append(KeepTogether(block))
        story.append(PageBreak())

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return out
