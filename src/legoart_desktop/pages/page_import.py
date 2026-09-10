"""Page 1 —— 图片导入 + 自由裁剪（D4：成品比例=裁剪比例）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from legoart.errors import LegoArtError
from ..widgets.crop_canvas import CropCanvas


class ImportPage(QWidget):
    """图片选择/裁剪页：完成后发射 cropped(PIL.Image)。"""

    cropped = pyqtSignal(object)
    go_home = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pil: Image.Image | None = None
        self.last_dir: str | None = None

        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_open = QPushButton("打开图片…")
        self.btn_open.clicked.connect(self._choose_file)
        self.btn_reset = QPushButton("重选裁剪")
        self.btn_reset.clicked.connect(self._reset_sel)
        self.btn_next = QPushButton("下一步 →")
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._emit_crop)
        top.addWidget(self.btn_open)
        top.addWidget(self.btn_reset)
        top.addStretch(1)
        top.addWidget(self.btn_next)
        lay.addLayout(top)

        self.canvas = CropCanvas()
        lay.addWidget(self.canvas, stretch=1)

        self.info = QLabel("未载入图片")
        lay.addWidget(self.info)

    # ---- 公共 API（测试/自动化可用）----
    def set_image_path(self, path: str | Path) -> None:
        self._load_image(path)

    def current_image(self) -> Image.Image | None:
        return self._pil

    def crop_image(self) -> Image.Image:
        """返回当前裁剪（未框选 = 整幅）。"""
        if self._pil is None:
            raise LegoArtError("尚未载入图片", code="ERR_DATA")
        rect = self.canvas.selection_rect()
        if rect is None:
            return self._pil.copy()
        left, t = rect.left(), rect.top()
        r = min(left + rect.width(), self._pil.width)
        b = min(t + rect.height(), self._pil.height)
        return self._pil.crop((left, t, r, b))

    # ---- 内部 ----
    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            self.last_dir or "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*)",
        )
        if path:
            self.last_dir = str(Path(path).parent)
            try:
                self._load_image(path)
            except LegoArtError as e:
                self.info.setText(str(e))

    def _load_image(self, path: str | Path) -> None:
        from legoart.mosaic.sampling import load_rgb_image

        pil = load_rgb_image(path)
        self._pil = pil
        self.canvas.set_image(pil)
        self.btn_next.setEnabled(True)
        self.info.setText(
            f"原图 {pil.width}×{pil.height} px ｜ 框选后比例为裁剪比例（下一步只需输入宽度）"
        )

    def _reset_sel(self) -> None:
        self.canvas.clear_selection()

    def _emit_crop(self) -> None:
        if self._pil is None:
            return
        img = self.crop_image()
        if img.width < 4 or img.height < 4:
            self.info.setText("裁剪区域过小（≥4px）")
            return
        self.cropped.emit(img)
