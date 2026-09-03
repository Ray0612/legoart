"""拍照识别入库对话框（M6）。

流程：选图 → 识别（YOLO 优先 / opencv 分割兜底）→ 候选逐行出现：
  颜色（识别结果，可改）｜ ΔE00｜ 零件形态（用户下拉确认，可改）｜ 数量
→ 「全部入库」（source=photo）。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from legoart import api
from legoart.detect import PartCandidate, resolve_detector

from ..store import InventoryStore


class PhotoEntryDialog(QDialog):
    accepted_count = pyqtSignal(int)

    def __init__(self, store: InventoryStore, parent=None, *, detector=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("拍照识别入库（颜色识别 + 手动确认形态）")
        self.resize(860, 480)
        self.store = store
        self._catalog = api.load_catalog()
        self._palette = api.build_palette(self._catalog)
        self._detector = detector or resolve_detector(self._palette)[0]
        self._rgb: np.ndarray | None = None
        self._cands: list[PartCandidate] = []
        self._row_widgets: list[tuple[QComboBox, QComboBox, QSpinBox]] = []

        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_open = QPushButton("选择照片…")
        self.btn_open.clicked.connect(self._choose)
        self.btn_detect = QPushButton("识别零件")
        self.btn_detect.setEnabled(False)
        self.btn_detect.clicked.connect(self._detect)
        self.btn_import = QPushButton("全部入库")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self._import_all)
        self.lbl_status = QLabel("（识别结果的颜色需人工复核，形态请下拉选择）")
        top.addWidget(self.btn_open)
        top.addWidget(self.btn_detect)
        top.addWidget(self.btn_import)
        top.addStretch(1)
        lay.addLayout(top)
        lay.addWidget(self.lbl_status)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["#", "颜色", "ΔE00", "零件形态", "数量", "区域(px)"])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table, 1)

    # ---- 图片 ----
    def _choose(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择散落积木照片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*)"
        )
        if path:
            self.load_and_detect(path)

    def load_and_detect(self, path: str | Path) -> None:
        """测试/自动化入口：载图 + 识别。"""
        im = Image.open(path).convert("RGB")
        self._rgb = np.asarray(im, dtype=np.uint8)
        self.lbl_status.setText(f"已载入 {im.width}×{im.height}，点击“识别零件”")
        self.btn_detect.setEnabled(True)
        self.btn_import.setEnabled(False)

    def _detect(self) -> None:
        if self._rgb is None:
            return
        cands = self._detector.predict(self._rgb)
        self._cands = cands
        self._populate_rows()
        if not cands:
            self.lbl_status.setText("未识别到候选色块（可换图或调低默认灵敏度，形态手动确认）")
        else:
            self.lbl_status.setText(f"识别到 {len(cands)} 个候选（颜色为自动匹配，请复核；形态请选择）")
            self.btn_import.setEnabled(True)

    # ---- 行 ----
    def _populate_rows(self) -> None:
        self.table.setRowCount(0)
        self._row_widgets = []
        for i, c in enumerate(self._cands):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            color_combo = self._color_combo(c.palette_color_id)
            self.table.setCellWidget(i, 1, color_combo)
            de_item = QTableWidgetItem(f"{c.delta:.1f}")
            self.table.setItem(i, 2, de_item)
            part_combo = self._part_combo()
            self.table.setCellWidget(i, 3, part_combo)
            qty = QSpinBox()
            qty.setRange(1, 999)
            qty.setValue(1)
            self.table.setCellWidget(i, 4, qty)
            self.table.setItem(i, 5, QTableWidgetItem(f"{c.w}×{c.h}"))
            self._row_widgets.append((color_combo, part_combo, qty))

    def _color_combo(self, default: str) -> QComboBox:
        combo = QComboBox()
        for col in self._catalog.colors:
            combo.addItem(f"{col.name_bl}（{col.rgb_hex}）", col.color_id)
        idx = combo.findData(default)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        return combo

    def _part_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setMinimumWidth(180)
        parts = sorted(self._catalog.parts, key=lambda p: (p.shape_family != "plate", p.name))
        for p in parts:
            combo.addItem(f"{p.design_id} · {p.name}", p.design_id)
        return combo

    # ---- 入库 ----
    def _import_all(self) -> None:
        add: list[tuple[str, str, int]] = []
        for color_combo, part_combo, qty in self._row_widgets:
            add.append((part_combo.currentData(), color_combo.currentData(), qty.value()))
        merged: Counter = Counter((d, c) for d, c, _ in add)
        rows: list[tuple[str, str, int]] = []
        for (d, c) in merged:
            rows.append((d, c, sum(q for dd, cc, q in add if (dd, cc) == (d, c))))
        try:
            self.store.add(rows, source="photo", note="photo-entry")
        except Exception as e:
            QMessageBox.warning(self, "入库失败", str(e))
            return
        self.accepted_count.emit(len(add))
        self.lbl_status.setText(f"已入库 {len(add)} 条（同件同色已累加）")
        self.btn_import.setEnabled(False)
