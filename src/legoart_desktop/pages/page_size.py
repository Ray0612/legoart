"""Page 2 —— 参数 + 生成（D3：输入宽度，高度按比例自动；D10 单位换算）。"""

from __future__ import annotations

import io

from PIL import Image
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from legoart import api
from legoart.model import ImageSpec
from legoart.model.image_spec import StyleKind

from ..workers import GenerationWorker


class SizePage(QWidget):
    """尺寸/选项/生成页：finished_ok(MosaicPlan) / failed(str)。"""

    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)
    back = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pil: Image.Image | None = None
        self._worker: GenerationWorker | None = None

        lay = QVBoxLayout(self)
        form = QFormLayout()

        unit_row = QHBoxLayout()
        self.rb_studs = QRadioButton("Studs（颗粒）")
        self.rb_cm = QRadioButton("cm（厘米）")
        self.rb_studs.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self.rb_studs)
        grp.addButton(self.rb_cm)
        unit_row.addWidget(self.rb_studs)
        unit_row.addWidget(self.rb_cm)
        unit_row.addStretch(1)
        form.addRow("宽度单位", unit_row)

        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(1, 4096)
        self.spin_w.setValue(48)
        self.spin_w.setDecimals(1)
        form.addRow("宽度", self.spin_w)

        self.lbl_hint = QLabel("输入宽度后，高度将按裁剪比例自动计算")
        form.addRow("", self.lbl_hint)

        self.combo_color = QComboBox()
        self.combo_color.addItem("仅常用色（推荐）", "recommended")
        self.combo_color.addItem("全部颜色", "all")
        form.addRow("候选色集", self.combo_color)

        self.chk_saliency = None
        from PyQt6.QtWidgets import QCheckBox

        self.chk_saliency = QCheckBox("AI 重点识别 → 凸起（可后续微调）")
        self.chk_saliency.setChecked(True)
        form.addRow("凸起", self.chk_saliency)

        # ---- 库存约束（D7/D13）----
        self.chk_inv = QCheckBox("库存约束模式（使用我的库存）")
        self.chk_inv.toggled.connect(self._inv_toggled)
        form.addRow("模式", self.chk_inv)

        self.combo_strategy = QComboBox()
        self.combo_strategy.addItem("近似替代（牺牲精度）", "approximate")
        self.combo_strategy.addItem("生成缺件清单（保留原色）", "missing_list")
        self.combo_strategy.addItem("极限拼搭（只用库存，缺处留空）", "extreme")
        self.combo_strategy.setEnabled(False)
        form.addRow("缺货策略", self.combo_strategy)

        self.btn_inventory = QPushButton("管理我的库存…")
        self.btn_inventory.setEnabled(False)
        self.btn_inventory.clicked.connect(self._open_inventory)
        form.addRow("", self.btn_inventory)

        self.lbl_inv = QLabel("理想购物车模式：输出需购买零件清单（不涉及扣减）")
        form.addRow("", self.lbl_inv)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_back = QPushButton("← 上一步")
        self.btn_back.clicked.connect(self.back.emit)
        self.btn_generate = QPushButton("生成方案")
        self.btn_generate.clicked.connect(self._start)
        btn_row.addWidget(self.btn_back)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_generate)
        lay.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

    # ---- 公共 API ----
    def set_image_pil(self, pil: Image.Image) -> None:
        self._pil = pil.convert("RGB")
        # cm→studs 换算提示
        self.rb_cm.setText(f"cm（厘米，1 stud≈0.8cm；宽度 38.4cm≈48 studs）")
        ratio = pil.width / pil.height
        self._aspect = ratio
        self.lbl_hint.setText(
            f"裁剪比例 {ratio:.3f}:1 —— 输入宽度后高度自动为宽度/{ratio:.3f}"
        )

    def build_spec(self) -> ImageSpec:
        unit = "cm" if self.rb_cm.isChecked() else "studs"
        w = float(self.spin_w.value())
        if unit == "cm":
            w = max(1.0, round(w / 0.8))
        from legoart.model.image_spec import ShortageStrategy

        return ImageSpec(
            grid_w=int(round(w)),
            grid_h=0,  # pipeline 按图片比例自动
            style=StyleKind.COLOR_BLOCK,
            use_inventory=self.chk_inv.isChecked(),
            shortage_strategy=ShortageStrategy(self.combo_strategy.currentData()),
            color_set=self.combo_color.currentData(),
            saliency_enabled=self.chk_saliency.isChecked(),
            input_unit=unit,
            catalog_version=api.load_catalog().version,
        )

    def _inv_toggled(self, on: bool) -> None:
        self.combo_strategy.setEnabled(on)
        self.btn_inventory.setEnabled(on)
        self.lbl_inv.setText(
            "库存约束模式：先耗库存，缺货按所选策略处理；确认拼搭后自动扣减"
            if on
            else "理想购物车模式：输出需购买零件清单（不涉及扣减）"
        )

    def _open_inventory(self) -> None:
        from .page_inventory import InventoryDialog
        from ..store import InventoryStore

        dlg = InventoryDialog(InventoryStore(), self)
        dlg.exec()

    def run_sync(self) -> object:
        """同步生成（测试/自动化）：直接返回 MosaicPlan。"""
        if self._pil is None:
            raise ValueError("未设置图片")
        spec = self.build_spec()
        return api.generate_plan(io.BytesIO(_png_bytes(self._pil)), spec)

    def _start(self) -> None:
        if self._pil is None:
            return
        spec = self.build_spec()
        self.btn_generate.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self._worker = GenerationWorker(_png_bytes(self._pil), spec, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_ok)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_progress(self, _stage: str, frac: float) -> None:
        self.progress.setValue(int(frac * 1000))

    def _on_ok(self, plan: object) -> None:
        self.progress.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.finished_ok.emit(plan)

    def _on_fail(self, msg: str) -> None:
        self.progress.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.failed.emit(msg)


def _png_bytes(pil: Image.Image) -> bytes:
    buf = io.BytesIO()
    pil.convert("RGB").save(buf, "PNG")
    return buf.getvalue()
