"""库存 DAO 测试：增减/不足回滚/快照/扣减+历史原子性。"""

import pytest

from legoart.errors import StorageError
from legoart.storage import open_db
from legoart.storage.inventory_dao import (
    add_history,
    deduct_and_history,
    get_qty,
    list_inventory,
    snapshot,
    upsert_add,
)


@pytest.fixture()
def conn(tmp_path):
    c = open_db(tmp_path / "inv.db")
    yield c
    c.close()


def test_upsert_add_and_get(conn):
    upsert_add(conn, [("3024", "Red", 10), ("3020", "Blue", 5)], source="manual")
    assert get_qty(conn, "3024", "Red") == 10
    upsert_add(conn, [("3024", "Red", 3)])
    assert get_qty(conn, "3024", "Red") == 13
    upsert_add(conn, [("3024", "Red", -4)])
    assert get_qty(conn, "3024", "Red") == 9
    assert snapshot(conn) == {("3024", "Red"): 9, ("3020", "Blue"): 5}


def test_negative_rollback(conn):
    upsert_add(conn, [("3024", "Red", 5)])
    with pytest.raises(StorageError):
        upsert_add(conn, [("3024", "Red", -99)])
    assert get_qty(conn, "3024", "Red") == 5  # 未变化


def test_list_and_family_filter(conn):
    upsert_add(conn, [("3024", "Red", 1)])
    conn.execute(
        "INSERT INTO catalog_parts(design_id,name,category,stud_w,stud_h,shape_family) "
        "VALUES('3024','Plate 1 x 1','Plate',1,1,'plate')"
    )
    conn.execute(
        "INSERT INTO catalog_parts(design_id,name,category,stud_w,stud_h,shape_family) "
        "VALUES('3004','Brick 1 x 2','Brick',2,1,'brick')"
    )
    upsert_add(conn, [("3004", "Red", 2)])
    plates = list_inventory(conn, family="plate")
    assert [r["design_id"] for r in plates] == ["3024"]
    assert len(list_inventory(conn)) == 2


def test_deduct_and_history_atomic_ok(conn):
    upsert_add(conn, [("3024", "Red", 10)])
    hid = deduct_and_history(
        conn,
        [("3024", "Red", 4)],
        params_dict={"w": 8},
        plan_dict={"grid": {"w": 8}},
        allocations=[{"design_id": "3024", "color_id": "Red", "qty": 4}],
    )
    assert get_qty(conn, "3024", "Red") == 6
    row = conn.execute("SELECT params_json FROM project_history WHERE id=?", (hid,)).fetchone()
    assert '"w"' in row["params_json"]


def test_deduct_insufficient_rolls_back(conn):
    upsert_add(conn, [("3024", "Red", 3)])
    with pytest.raises(StorageError):
        deduct_and_history(
            conn, [("3024", "Red", 5)], params_dict={}, plan_dict={}, allocations=[]
        )
    assert get_qty(conn, "3024", "Red") == 3
    assert conn.execute("SELECT COUNT(*) c FROM project_history").fetchone()["c"] == 0


def test_add_history_smoke(conn):
    hid = add_history(conn, '{"a":1}', '{"b":2}')
    assert hid >= 1
