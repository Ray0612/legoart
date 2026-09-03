"""SQLite 存储：schema 初始化、meta、后续 DAO 复用。

Schema 依据技术方案 §8.1：inventory / project_history / catalog_* / meta。
原文档的 ``color_code``/``part_shape`` 列以视图别名保留兼容（见下方视图）。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..errors import StorageError

SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
  id INTEGER PRIMARY KEY,
  design_id  TEXT NOT NULL,
  color_id   TEXT NOT NULL,
  quantity   INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
  source     TEXT NOT NULL DEFAULT 'manual',   -- manual | excel | photo
  note       TEXT,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_inv ON inventory(design_id, color_id);

CREATE TABLE IF NOT EXISTS project_history (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  params_json TEXT NOT NULL,
  plan_snapshot_json TEXT NOT NULL,
  bom_excel_path TEXT,
  pdf_path TEXT
);

CREATE TABLE IF NOT EXISTS catalog_parts (
  design_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  stud_w INTEGER NOT NULL DEFAULT 1,
  stud_h INTEGER NOT NULL DEFAULT 1,
  shape_family TEXT NOT NULL DEFAULT 'other',
  extra TEXT
);
CREATE TABLE IF NOT EXISTS catalog_colors (
  color_id TEXT PRIMARY KEY,
  name_bl TEXT NOT NULL,
  name_tlg TEXT,
  rgb TEXT NOT NULL,
  is_trans INTEGER NOT NULL DEFAULT 0,
  material TEXT NOT NULL DEFAULT 'solid',
  recommended INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS catalog_elements (
  design_id TEXT NOT NULL,
  color_id TEXT NOT NULL,
  PRIMARY KEY (design_id, color_id)
);
"""

# 与原需求文档字段口径兼容的视图（color_code=color_id, part_shape=design_id+名称）
_COMPAT_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_inventory_legacy AS
SELECT i.id,
       i.color_id AS color_code,
       COALESCE(cp.name, i.design_id) AS part_shape,
       i.quantity, i.source, i.note, i.updated_at
FROM inventory i
LEFT JOIN catalog_parts cp ON cp.design_id = i.design_id;
"""


def connect(path: str | Path) -> sqlite3.Connection:
    """打开（必要时创建父目录）并返回带 Row 工厂、开启外键的连接。"""
    p = Path(path)
    if p.parent and not p.parent.exists():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"无法创建数据库目录 {p.parent}: {e}")
    try:
        conn = sqlite3.connect(str(p))
    except sqlite3.Error as e:
        raise StorageError(f"无法打开数据库 {p}: {e}")
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # 自动提交；显式 BEGIN/COMMIT 管理多语句事务
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """幂等建表 + 视图 + 写入 schema 版本。"""
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.executescript(_COMPAT_VIEW_SQL)
        set_meta(conn, "schema_version", str(SCHEMA_VERSION))
        conn.commit()
    except sqlite3.Error as e:
        raise StorageError(f"数据库初始化失败: {e}")


def get_meta(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def open_db(path: str | Path) -> sqlite3.Connection:
    """便捷入口：connect + init_schema。"""
    conn = connect(path)
    init_schema(conn)
    return conn
