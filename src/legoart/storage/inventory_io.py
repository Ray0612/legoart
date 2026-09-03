"""库存 Excel 导入/导出（D12：手动 + Excel + 拍照识别；拍照在 M6）。

格式：表头 design_id, color_id, quantity, note（首行）；其余行忽略。
导入时数值非法 → 抛 StorageError 并定位行号。
"""

from __future__ import annotations

from pathlib import Path

from ..errors import StorageError

_HEADERS = ["design_id", "color_id", "quantity", "note"]
_COLS = {h: i for i, h in enumerate(_HEADERS)}


def export_inventory_xlsx(path: str | Path, rows: list[dict]) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "inventory"
    ws.append(_HEADERS)
    for r in rows:
        ws.append(
            [r.get("design_id", ""), r.get("color_id", ""), int(r.get("quantity", 0)), r.get("note", "")]
        )
    for col, width in zip("ABCD", (12, 22, 10, 24), strict=True):
        ws.column_dimensions[col].width = width
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(p))


def import_inventory_xlsx(path: str | Path) -> list[dict]:
    from openpyxl import load_workbook

    p = Path(path)
    if not p.exists():
        raise StorageError(f"Excel 不存在: {p}")
    try:
        wb = load_workbook(str(p), read_only=True, data_only=True)
    except Exception as e:
        raise StorageError(f"Excel 无法打开: {e}") from e
    ws = wb.active
    out: list[dict] = []
    try:
        it = ws.iter_rows(values_only=True)
        header = next(it, None)
        if header is None or header[0] != "design_id":
            raise StorageError("首行表头须为 design_id,color_id,quantity[,note]")
        for i, row in enumerate(it, start=2):
            if row is None or all(v is None or str(v).strip() == "" for v in row):
                continue
            try:
                qty = int(row[2])
            except (TypeError, ValueError):
                raise StorageError(f"第 {i} 行 quantity 非法: {row[2]!r}")
            if qty <= 0:
                continue
            out.append(
                {
                    "design_id": str(row[0]).strip(),
                    "color_id": str(row[1]).strip(),
                    "quantity": qty,
                    "note": str(row[3]).strip() if len(row) > 3 and row[3] is not None else "",
                }
            )
    finally:
        wb.close()
    return out
