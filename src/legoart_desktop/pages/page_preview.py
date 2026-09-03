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
        self._inventory = None
        self._solver = None
        self._deducted = False

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

        # 库存约束求解结果（M4）
        self.solver_label = QLabel("")
        self.solver_label.setWordWrap(True)
        self.solver_label.setVisible(False)
        lay.addWidget(self.solver_label)

        self.btn_deduct = QPushButton("确认开始拼搭 → 扣减库存并记录历史")
        self.btn_deduct.setVisible(False)
        self.btn_deduct.clicked.connect(self._on_deduct)
        lay.addWidget(self.btn_deduct)

    # ---- 公共 API ----
    def set_plan(self, plan: MosaicPlan, *, inventory=None, solver=None) -> None:
        self._plan = plan
        self._inventory = inventory  # InventoryStore（仅库存模式）
        self._solver = solver        # SolverResult（仅库存模式）
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
        self._refresh_solver()

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

    def _refresh_solver(self) -> None:
        solver = self._solver
        inventory = self._inventory
        if solver is None:
            self.solver_label.setVisible(False)
            self.btn_deduct.setVisible(False)
            return
        lines = []
        alloc = solver.allocations
        placed = sum(a[2] for a in alloc)
        lines.append(f"库存可拼 {len(solver.placements)} 片（共 {placed} 件扣减）")
        if solver.substituted:
            lines.append(
                f"替代 {len(solver.substituted)} 处（如 2×1x2 → 1x4、近似色），"
                "详见 Excel 缺件/替代明细（M5）"
            )
        if solver.missing:
            top = solver.missing[:6]
            lines.append(
                "缺件：" + "，".join(f"{m.design_id} {m.color_id} ×{m.qty}" for m in top)
                + ("…" if len(solver.missing) > 6 else "")
            )
        if solver.warnings:
            lines.append("提示：" + "；".join(solver.warnings[:2]))
        self.solver_label.setText("\n".join(lines))
        self.solver_label.setVisible(True)
        show_deduct = bool(
            inventory is not None and alloc and not self._deducted
        )
        self.btn_deduct.setVisible(show_deduct)
        if self._deducted:
            self.solver_label.setText(self.solver_label.text() + "\n（已完成扣减并记录历史）")

    def _on_deduct(self) -> None:
        if self._plan is None or self._inventory is None or self._solver is None or self._deducted:
            return
        try:
            hid = self._inventory.deduct_and_record(self._solver.allocations, plan=self._plan)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "扣减失败", str(e))
            return
        self._deducted = True
        self.solver_label.setText(self.solver_label.text() + f"\n✓ 已扣减并记录历史（#{hid}）")
        self.btn_deduct.setVisible(False)

    def _choose_save(self) -> None:
        if self._plan is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存方案", "mosaic_plan.json", "JSON (*.json)"
        )
        if path:
            self.save_plan(path)
