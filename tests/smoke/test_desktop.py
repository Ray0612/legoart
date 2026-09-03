"""桌面端离屏冒烟（QT_QPA_PLATFORM=offscreen）。"""

import json
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication

from legoart_desktop.main_window import MainWindow
from legoart_desktop.pages.page_import import ImportPage
from legoart_desktop.pages.page_preview import PreviewPage
from legoart_desktop.pages.page_size import SizePage
from legoart_desktop.widgets.crop_canvas import CropCanvas
from legoart_desktop.workers import GenerationWorker


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _gradient_png(path, w=100, h=60):
    im = Image.new("RGB", (w, h))
    px = im.load()
    for x in range(w):
        for y in range(h):
            px[x, y] = (int(255 * x / w), int(120 * y / h), 60)
    im.save(path)
    return path


def test_crop_canvas_math(qapp):
    canvas = CropCanvas()
    canvas.set_image(Image.new("RGB", (100, 60), (0, 0, 0)))
    assert canvas.has_image()
    assert canvas.aspect_ratio() == pytest.approx(100 / 60)
    assert canvas.selection_rect() is None
    canvas.set_selection(QRect(10, 10, 50, 20))
    r = canvas.selection_rect()
    assert (r.width(), r.height()) == (50, 20)
    assert canvas.aspect_ratio() == pytest.approx(2.5)


def test_import_page_crop_flow(qapp, tmp_path):
    src = _gradient_png(tmp_path / "a.png")
    page = ImportPage()
    got = []
    page.cropped.connect(got.append)
    page.set_image_path(src)
    assert page.current_image().size == (100, 60)
    assert page.btn_next.isEnabled()
    # 无框选 → 整幅
    page.canvas.clear_selection()
    whole = page.crop_image()
    assert whole.size == (100, 60)
    # 框选下半 → 100×40
    page.canvas.set_selection(QRect(0, 20, 100, 40))
    cropped = page.crop_image()
    assert cropped.size == (100, 40)
    page._emit_crop()
    assert len(got) == 1 and got[0].size == (100, 40)


def test_size_page_run_sync(qapp):
    page = SizePage()
    page.set_image_pil(Image.new("RGB", (100, 60), (120, 40, 40)))
    page.spin_w.setValue(48)
    spec = page.build_spec()
    assert spec.grid_w == 48 and spec.grid_h == 0
    assert spec.input_unit == "studs"
    plan = page.run_sync()
    assert plan.grid.width == 48
    assert plan.grid.height == 29  # 100:60 → 48/1.6667
    assert plan.placements


def test_size_page_cm_unit(qapp):
    page = SizePage()
    page.set_image_pil(Image.new("RGB", (100, 60), (120, 40, 40)))
    page.rb_cm.setChecked(True)
    page.spin_w.setValue(38.4)
    spec = page.build_spec()
    assert spec.grid_w == 48  # 38.4cm / 0.8
    assert spec.input_unit == "cm"


def test_preview_page_and_save(qapp, tmp_path):
    page_size = SizePage()
    page_size.set_image_pil(Image.new("RGB", (100, 60), (30, 90, 160)))
    plan = page_size.run_sync()

    preview = PreviewPage()
    preview.set_plan(plan)
    assert preview.combo_layer.count() >= 1
    assert "网格 48×29" in preview.summary.text()
    assert "板件" in preview.summary.text()

    out = tmp_path / "plan.json"
    preview.save_plan(out)
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["grid"]["w"] == 48
    # 触发绘制（offscreen）
    preview.show()
    qapp.processEvents()


def test_worker_thread(qapp, tmp_path):
    from PyQt6.QtCore import QCoreApplication, QEvent

    from legoart.model import ImageSpec

    src = _gradient_png(tmp_path / "b.png", 40, 24)
    data = open(src, "rb").read()
    spec = ImageSpec(grid_w=16, grid_h=0)
    worker = GenerationWorker(data, spec)
    got = []
    worker.finished_ok.connect(got.append)
    worker.failed.connect(lambda m: got.append(None))
    worker.start()
    deadline = time.time() + 15
    while not got and worker.isRunning() and time.time() < deadline:
        # 无完整事件循环（离屏测试）时需手动投递跨线程排队信号
        QCoreApplication.sendPostedEvents(None, QEvent.Type.MetaCall)
        qapp.processEvents()
        time.sleep(0.02)
    worker.wait(2000)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.MetaCall)
    qapp.processEvents()
    assert got and got[0] is not None


def test_main_window_end_to_end(qapp, tmp_path):
    src = _gradient_png(tmp_path / "c.png", 80, 40)
    win = MainWindow()
    win.show()
    qapp.processEvents()
    assert win.pages.count() == 3
    assert "目录" in win.status.text()

    # 全链路（同步驱动信号链）
    win.page_import.set_image_path(src)
    win._on_cropped(win.page_import.crop_image())
    assert win.pages.currentWidget() is win.page_size
    plan = win.page_size.run_sync()
    win._on_plan(plan)
    assert win.pages.currentWidget() is win.page_preview
    assert win.page_preview.combo_layer.count() >= 1
    win.close()


def test_inventory_dialog_list(qapp, tmp_path):
    from legoart_desktop.pages.page_inventory import InventoryDialog
    from legoart_desktop.store import InventoryStore

    store = InventoryStore(tmp_path / "inv.db")
    store.add([("3024", "Red", 20), ("3020", "Blue", 4)])
    dlg = InventoryDialog(store)
    assert dlg.table.rowCount() == 2

    # 显式选中 3024 + Red，累加 5 → 同 key 合并
    for i in range(dlg.combo_part.count()):
        if dlg.combo_part.itemData(i) == "3024":
            dlg.combo_part.setCurrentIndex(i)
            break
    for i in range(dlg.combo_color.count()):
        if dlg.combo_color.itemData(i) == "Red":
            dlg.combo_color.setCurrentIndex(i)
            break
    dlg.spin_qty.setValue(5)
    dlg._on_add()
    assert dlg.table.rowCount() == 2
    assert store.snapshot() == {("3024", "Red"): 25, ("3020", "Blue"): 4}


def test_inventory_mode_solve_and_deduct(qapp, tmp_path, monkeypatch):
    from collections import Counter

    from legoart_desktop.store import InventoryStore

    db = tmp_path / "u.db"
    monkeypatch.setenv("LEGOART_DB", str(db))

    # 1) 纯色图 → 确定性方案
    im = Image.new("RGB", (24, 24), (150, 40, 40))
    page = SizePage()
    page.set_image_pil(im)
    page.spin_w.setValue(8)
    page.chk_inv.setChecked(True)
    page.combo_strategy.setCurrentIndex(0)  # 近似替代
    plan = page.run_sync()
    assert plan.spec.use_inventory is True

    # 2) 按方案需求备货（精确件）
    store = InventoryStore()
    counts = Counter((p.design_id, p.color_id) for p in plan.placements)
    store.add([(d, c, q) for (d, c), q in counts.items()])
    assert store.snapshot()

    # 3) 主窗口装配求解
    win = MainWindow()
    win._on_plan(plan)
    assert win.pages.currentWidget() is win.page_preview
    preview = win.page_preview
    assert preview._solver is not None
    assert len(preview._solver.missing) == 0
    assert preview._solver.allocations
    assert not preview.btn_deduct.isHidden()  # 未 show 的窗口 isVisible 恒 False
    assert "可拼" in preview.solver_label.text()

    # 4) 确认拼搭 → 扣减 + 历史
    preview._on_deduct()
    assert all(r["quantity"] == 0 for r in store.list())
    import sqlite3

    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(*) FROM project_history").fetchone()[0]
    conn.close()
    assert n == 1
    assert preview.btn_deduct.isHidden()
    win.close()
