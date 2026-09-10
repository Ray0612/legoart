"""SQLite 存储测试：schema / meta / 库存与视图兼容层。"""

import sqlite3

import pytest

from legoart.errors import StorageError
from legoart.storage import get_meta, init_schema, open_db, set_meta


def test_open_db_creates_schema(tmp_path):
    db = tmp_path / "u.db"
    conn = open_db(db)
    try:
        assert get_meta(conn, "schema_version") == "1"
        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"inventory", "project_history", "catalog_parts", "meta"} <= tables
    finally:
        conn.close()


def test_init_idempotent(tmp_path):
    conn = open_db(tmp_path / "u.db")
    init_schema(conn)  # 二次执行不报错
    conn.close()


def test_meta_roundtrip(tmp_path):
    conn = open_db(tmp_path / "u.db")
    set_meta(conn, "catalog_version", "curated-v0")
    assert get_meta(conn, "catalog_version") == "curated-v0"
    set_meta(conn, "catalog_version", "v1")
    assert get_meta(conn, "catalog_version") == "v1"
    assert get_meta(conn, "missing", "d") == "d"
    conn.close()


def test_inventory_insert_and_unique(tmp_path):
    conn = open_db(tmp_path / "u.db")
    conn.execute(
        "INSERT INTO inventory(design_id, color_id, quantity, source, updated_at) VALUES(?,?,?,?,?)",
        ("3024", "Red", 100, "manual", "2026-09-03T00:00:00"),
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO inventory(design_id, color_id, quantity, source, updated_at) VALUES(?,?,?,?,?)",
            ("3024", "Red", 1, "manual", "2026-09-03T00:00:00"),
        )
    conn.close()


def test_legacy_view_aliases(tmp_path):
    """原文档字段口径 color_code / part_shape 通过视图可见。"""
    conn = open_db(tmp_path / "u.db")
    conn.execute(
        "INSERT INTO catalog_parts(design_id, name, category, stud_w, stud_h, shape_family) "
        "VALUES('3024','Plate 1 x 1','Plate',1,1,'plate')"
    )
    conn.execute(
        "INSERT INTO inventory(design_id, color_id, quantity, source, updated_at) VALUES(?,?,?,?,?)",
        ("3024", "Red", 5, "excel", "2026-09-03T00:00:00"),
    )
    row = conn.execute(
        "SELECT color_code, part_shape, quantity FROM v_inventory_legacy"
    ).fetchone()
    assert row["color_code"] == "Red"
    assert row["part_shape"] == "Plate 1 x 1"
    assert row["quantity"] == 5
    conn.close()


def test_history_roundtrip_json(tmp_path):
    conn = open_db(tmp_path / "u.db")
    conn.execute(
        "INSERT INTO project_history(created_at, params_json, plan_snapshot_json) VALUES(?,?,?)",
        ("t", '{"w":48}', '{"bom":[]}'),
    )
    row = conn.execute("SELECT params_json FROM project_history").fetchone()
    assert '"w"' in row["params_json"]
    conn.close()


def test_open_bad_dir_raises(tmp_path):
    # 跨平台：让父级是一个「文件」，无论 Windows/Linux 都无法作为目录打开数据库
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(StorageError):
        open_db(blocker / "u.db")
