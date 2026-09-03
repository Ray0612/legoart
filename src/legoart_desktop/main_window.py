"""主窗口：三页向导（导入裁剪 → 参数生成 → 预览保存）。"""

from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMainWindow, QMessageBox, QStackedWidget, QStatusBar

from legoart import api

from .pages.page_import import ImportPage
from .pages.page_preview import PreviewPage
from .pages.page_size import SizePage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("乐高画作智能转换器 · LEGO Art Converter")
        self.resize(1040, 720)

        self.pages = QStackedWidget(self)

        self.page_import = ImportPage()
        self.page_size = SizePage()
        self.page_preview = PreviewPage()

        for w in (self.page_import, self.page_size, self.page_preview):
            self.pages.addWidget(w)

        self.page_import.cropped.connect(self._on_cropped)
        self.page_import.go_home.connect(lambda: self.pages.setCurrentWidget(self.page_import))
        self.page_size.back.connect(lambda: self.pages.setCurrentWidget(self.page_import))
        self.page_size.finished_ok.connect(self._on_plan)
        self.page_size.failed.connect(self._on_generate_failed)
        self.page_preview.back.connect(lambda: self.pages.setCurrentWidget(self.page_size))

        self.setCentralWidget(self.pages)
        self._install_status()

    def _install_status(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)
        cat = api.load_catalog()
        self.status = QLabel(
            f"目录 v{cat.version}：{len(cat.colors)} 色 / {len(cat.parts)} 件 ｜ 本地计算 ｜ M3"
        )
        bar.addWidget(self.status)

    # ---- 事件 ----
    def _on_cropped(self, pil: Image.Image) -> None:
        self.page_size.set_image_pil(pil)
        self.pages.setCurrentWidget(self.page_size)

    def _on_plan(self, plan) -> None:
        self.page_preview.set_plan(plan)
        self.pages.setCurrentWidget(self.page_preview)

    def _on_generate_failed(self, msg: str) -> None:
        QMessageBox.warning(self, "生成失败", msg)
