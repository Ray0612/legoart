"""Page 3 —— 预览（分层视图 + 统计 + 保存方案 JSON）。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from legoart import api
from legoart.model import MosaicPlan

from ..widgets.mosaic_view import MosaicView


class PreviewPage(QWidget):
    back = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._plan: MosaicPlan | None = None
        self._palette = None

        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_back = QPushButton("← 重新生成")
        self.btn_back.clicked.connect(self.back.emit)
        self.btn_save = QPushButton("保存方案 JSON…")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._choose_save)
        top.addWidget(self.btn_back)
        top.addStretch(1)
        top.addWidget(self.btn_save)
        lay.addLayout(top)

        self.combo_layer = QComboBox()
        self.combo_layer.currentIndexChanged.connect(self._refresh_view)
        lay.addWidget(self.combo_layer)

        self.view = MosaicView()
        lay.addWidget(self.view, stretch=1)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)

    # ---- 公共 API ----
    def set_plan(self, plan: MosaicPlan) -> None:
        self._plan = plan
        self._palette = api.build_palette()
        self.combo_layer.blockSignals(True)
        self.combo_layer.clear()
        stack = plan.stack
        for layer in sorted(stack.layers, key=lambda x: x.level):
            self.combo_layer.addItem(f"物理层 {layer.level}", layer.level)
        self.combo_layer.blockSignals(False)
        self.btn_save.setEnabled(True)
        self._refresh_view()
        self._refresh_summary()

    def current_plan(self) -> MosaicPlan | None:
        return self._plan

    def save_plan(self, path: str | Path) -> None:
        import json

        if self._plan is None:
            return
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self._plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---- 内部 ----
    def _refresh_view(self) -> None:
        if self._plan is None:
            return
        grid = self._plan.grid_layer(self.combo_layer.currentData())
        self.view.set_content(grid, self._palette)

    def _refresh_summary(self) -> None:
        plan = self._plan
        if plan is None:
            return
        stack = plan.stack
        covered = sum(p.area for p in plan.placements)
        pieces = len(plan.placements)
        regions = plan.regions.regions
        text = (
            f"网格 {plan.grid.width}×{plan.grid.height} studs（{plan.grid.width * plan.grid.height} 格）\n"
            f"颜色 {len(set(plan.grid.colors.ravel().tolist()))} 种 ｜ 物理层 {stack.height_total} 层 ｜ "
            f"凸起区域 {len(regions)} 处{('（层数 ' + ','.join(str(r.raise_layers) for r in regions) + '）') if regions else ''}\n"
            f"合并后板件 {pieces} 片（覆盖 {covered} 格）｜ 用时 {plan.elapsed_ms} ms"
        )
        if plan.warnings:
            text += "\n提示：" + "；".join(plan.warnings[:2])
        self.summary.setText(text)

    def _choose_save(self) -> None:
        if self._plan is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存方案", "mosaic_plan.json", "JSON (*.json)"
        )
        if path:
            self.save_plan(path)
