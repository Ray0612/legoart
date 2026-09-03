"""库存/历史 DAO：单连接 API（每次调用自行 BEGIN/COMMIT，事务原子）。

扣减语义（原文档 §2.4）：仅"确认开始拼搭"后扣减；扣成负数即抛 StorageError
并整体回滚。project_history 记录参数 + 方案快照 + 扣减明细（可回放）。
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone

from ..errors import StorageError

StockKey = tuple[str, str]  # (design_id, color_id)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_inventory(conn: sqlite3.Connection, *, family: str | None = None) -> list[dict]:
    """库存全表（可过滤 family=plate|brick|...），按设计号/颜色排序。"""
    sql = """
        SELECT i.id, i.design_id, i.color_id, i.quantity, i.source, i.note, i.updated_at,
               cp.name AS part_name, cp.shape_family, cp.stud_w, cp.stud_h
        FROM inventory i LEFT JOIN catalog_parts cp ON cp.design_id = i.design_id
    """
    params: tuple = ()
    if family:
        sql += " WHERE cp.shape_family = ?"
        params = (family,)
    sql += " ORDER BY i.design_id, i.color_id"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def snapshot(conn: sqlite3.Connection, *, family: str | None = None) -> dict[StockKey, int]:
    """库存快照 (design_id,color_id)->qty（求解用，仅 plate 足够；family 可选）。"""
    rows = list_inventory(conn, family=family)
    out: dict[StockKey, int] = {}
    for r in rows:
        if r["quantity"] > 0:
            out[(r["design_id"], r["color_id"])] = r["quantity"]
    return out


def get_qty(conn: sqlite3.Connection, design_id: str, color_id: str) -> int:
    row = conn.execute(
        "SELECT quantity FROM inventory WHERE design_id=? AND color_id=?", (design_id, color_id)
    ).fetchone()
    return int(row["quantity"]) if row else 0


def upsert_add(conn: sqlite3.Connection, rows: Iterable[tuple[str, str, int]], *, source: str = "manual", note: str | None = None) -> None:
    """按 (design_id, color_id, qty_delta) 批量增/减（delta 可为负）；结果 <0 抛错。"""
    try:
        conn.execute("BEGIN")
        for design_id, color_id, delta in rows:
            delta = int(delta)
            cur = get_qty(conn, design_id, color_id)
            if cur + delta < 0:
                raise StorageError(
                    f"库存不足：{design_id} {color_id} 现 {cur}，需 {-delta}", code="ERR_STOCK"
                )
            if cur == 0 and delta > 0:
                conn.execute(
                    "INSERT INTO inventory(design_id, color_id, quantity, source, note, updated_at) "
                    "VALUES(?,?,?,?,?,?)",
                    (design_id, color_id, delta, source, note, _ts()),
                )
            else:
                conn.execute(
                    "UPDATE inventory SET quantity = quantity + ?, source = ?, note = COALESCE(?, note), "
                    "updated_at = ? WHERE design_id = ? AND color_id = ?",
                    (delta, source, note, _ts(), design_id, color_id),
                )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise StorageError(f"库存更新失败: {e}") from e
    except StorageError:
        conn.rollback()
        raise


def delete_row(conn: sqlite3.Connection, row_id: int) -> None:
    conn.execute("DELETE FROM inventory WHERE id = ?", (row_id,))
    conn.commit()


def add_history(
    conn: sqlite3.Connection,
    params_json: str,
    snapshot_json: str,
    *,
    bom_excel_path: str | None = None,
    pdf_path: str | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO project_history(created_at, params_json, plan_snapshot_json, bom_excel_path, pdf_path) "
        "VALUES(?,?,?,?,?)",
        (_ts(), params_json, snapshot_json, bom_excel_path, pdf_path),
    )
    conn.commit()
    return int(cur.lastrowid)


def deduct_and_history(
    conn: sqlite3.Connection,
    demands: Iterable[tuple[str, str, int]],
    *,
    params_dict: dict,
    plan_dict: dict,
    allocations: list[dict],
) -> int:
    """【确认开始拼搭】单事务：扣减 + 写历史快照（含扣减明细）。"""
    try:
        conn.execute("BEGIN")
        for design_id, color_id, qty in demands:
            qty = int(qty)
            cur = get_qty(conn, design_id, color_id)
            if cur < qty:
                raise StorageError(
                    f"库存不足：{design_id} {color_id} 现 {cur}，需 {qty}", code="ERR_STOCK"
                )
            conn.execute(
                "UPDATE inventory SET quantity = quantity - ?, updated_at = ? "
                "WHERE design_id = ? AND color_id = ?",
                (qty, _ts(), design_id, color_id),
            )
        record = {
            "allocations": allocations,
            "deducted_at": _ts(),
        }
        payload = {"params": params_dict, "plan": plan_dict, "deduct": record}
        cur = conn.execute(
            "INSERT INTO project_history(created_at, params_json, plan_snapshot_json) VALUES(?,?,?)",
            (_ts(), json.dumps(params_dict, ensure_ascii=False),
             json.dumps(payload, ensure_ascii=False)),
        )
        history_id = int(cur.lastrowid)
        conn.commit()
        return history_id
    except sqlite3.Error as e:
        conn.rollback()
        raise StorageError(f"扣减失败: {e}") from e
    except StorageError:
        conn.rollback()
        raise
