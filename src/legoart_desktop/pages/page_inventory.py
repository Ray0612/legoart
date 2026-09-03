"""库存管理对话框：CRUD + Excel 导入导出（拍照识别在 M6 接入占位）。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from legoart import api

from ..store import InventoryStore


class InventoryDialog(QDialog):
    def __init__(self, store: InventoryStore, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("我的积木库存")
        self.resize(760, 520)
        self.store = store
        self._catalog = api.load_catalog()
        self._palette = api.build_palette(self._catalog)

        lay = QVBoxLayout(self)
        add_row = QHBoxLayout()
        self.combo_part = QComboBox()
        self.combo_part.setMinimumWidth(220)
        parts = self._catalog.parts
        # 常用件在前：板 + 常见件（按名称）
        for p in sorted(parts, key=lambda p: (p.shape_family != "plate", p.name)):
            self.combo_part.addItem(f"{p.design_id} · {p.name}（{p.stud_w}x{p.stud_h} studs）", p.design_id)
        self.combo_color = QComboBox()
        for c in self._catalog.colors:
            r = c.rgb
            self.combo_color.addItem(
                f"{c.name_bl}（{c.rgb_hex}）", c.color_id
            )
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 100000)
        self.spin_qty.setValue(10)
        self.btn_add = QPushButton("入库（累加）")
        self.btn_add.clicked.connect(self._on_add)
        add_row.addWidget(QLabel("零件"))
        add_row.addWidget(self.combo_part, 1)
        add_row.addWidget(QLabel("颜色"))
        add_row.addWidget(self.combo_color)
        add_row.addWidget(QLabel("数量"))
        add_row.addWidget(self.spin_qty)
        add_row.addWidget(self.btn_add)
        lay.addLayout(add_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "设计号", "颜色", "数量", "来源"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table, 1)

        ops = QHBoxLayout()
        self.btn_delete = QPushButton("删除选中行")
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_excel_import = QPushButton("Excel 导入…")
        self.btn_excel_import.clicked.connect(self._on_import)
        self.btn_excel_export = QPushButton("导出 Excel…")
        self.btn_excel_export.clicked.connect(self._on_export)
        self.btn_photo = QPushButton("拍照识别（M6）")
        self.btn_photo.setEnabled(False)
        self.btn_photo.setToolTip("拍照识别将在 M6 里程碑接入")
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh)
        ops.addWidget(self.btn_delete)
        ops.addWidget(self.btn_excel_import)
        ops.addWidget(self.btn_excel_export)
        ops.addWidget(self.btn_photo)
        ops.addStretch(1)
        ops.addWidget(self.btn_refresh)
        lay.addLayout(ops)

        self.refresh()

    # ---- 操作 ----
    def refresh(self) -> None:
        rows = self.store.list()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, key in enumerate(("id", "design_id", "color_id", "quantity", "source")):
                item = QTableWidgetItem(str(r.get(key, "")))
                if j == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, j, item)

    def _on_add(self) -> None:
        design = self.combo_part.currentData()
        color = self.combo_color.currentData()
        qty = self.spin_qty.value()
        try:
            self.store.add([(design, color, qty)], source="manual", note="gui")
        except Exception as e:
            QMessageBox.warning(self, "入库失败", str(e))
            return
        self.refresh()

    def _on_delete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一行")
            return
        row_id = int(self.table.item(row, 0).text())
        self.store.delete(row_id)
        self.refresh()

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入库存 Excel", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            n = self.store.import_xlsx(path)
            QMessageBox.information(self, "完成", f"导入 {n} 行（累加入库）")
        except Exception as e:
            QMessageBox.warning(self, "导入失败", str(e))
        self.refresh()

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出库存 Excel", "inventory.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            self.store.export_xlsx(path)
            QMessageBox.information(self, "完成", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
