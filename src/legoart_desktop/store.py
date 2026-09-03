"""桌面库存存储封装（内部包 open_db/DAO）。默认库：LEGOART_DB 或 ./userdata.db。"""

from __future__ import annotations

import os
from pathlib import Path

from legoart.storage import open_db
from legoart.storage.inventory_dao import (
    add_history,
    deduct_and_history,
    delete_row,
    list_inventory,
    snapshot,
    upsert_add,
)
from legoart.storage.inventory_io import export_inventory_xlsx, import_inventory_xlsx


def default_db_path() -> Path:
    env = os.environ.get("LEGOART_DB")
    if env:
        return Path(env)
    return Path.cwd() / "userdata.db"


class InventoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = open_db(self.path)
        conn.close()  # 确保 schema 存在

    def list(self, *, family: str | None = None) -> list[dict]:
        conn = open_db(self.path)
        try:
            return list_inventory(conn, family=family)
        finally:
            conn.close()

    def snapshot(self, *, family: str | None = None) -> dict:
        conn = open_db(self.path)
        try:
            return snapshot(conn, family=family)
        finally:
            conn.close()

    def add(self, rows: list[tuple[str, str, int]], *, source: str = "manual", note: str | None = None) -> None:
        conn = open_db(self.path)
        try:
            upsert_add(conn, rows, source=source, note=note)
        finally:
            conn.close()

    def set_qty(self, design_id: str, color_id: str, qty: int, *, source: str = "manual") -> None:
        conn = open_db(self.path)
        try:
            from legoart.storage.inventory_dao import get_qty

            cur = get_qty(conn, design_id, color_id)
            upsert_add(conn, [(design_id, color_id, qty - cur)], source=source)
        finally:
            conn.close()

    def delete(self, row_id: int) -> None:
        conn = open_db(self.path)
        try:
            delete_row(conn, row_id)
        finally:
            conn.close()

    def import_xlsx(self, path: str | Path) -> int:
        rows = import_inventory_xlsx(path)
        if rows:
            self.add(
                [(r["design_id"], r["color_id"], r["quantity"]) for r in rows],
                source="excel",
                note="excel-import",
            )
        return len(rows)

    def export_xlsx(self, path: str | Path) -> None:
        export_inventory_xlsx(path, self.list())

    def deduct_and_record(self, allocations: list[tuple[str, str, int]], *, plan) -> int:
        """确认拼搭：扣减 + 历史快照，返回 history id。plan 为 MosaicPlan。"""
        conn = open_db(self.path)
        try:
            return deduct_and_history(
                conn,
                allocations,
                params_dict=plan.spec.to_dict(),
                plan_dict=plan.to_dict(),
                allocations=[
                    {"design_id": d, "color_id": c, "qty": q} for d, c, q in allocations
                ],
            )
        finally:
            conn.close()

    def add_history_json(self, params_json: str, snapshot_json: str) -> int:
        conn = open_db(self.path)
        try:
            return add_history(conn, params_json, snapshot_json)
        finally:
            conn.close()
