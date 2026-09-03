"""桌面应用入口逻辑（app.run）。"""

from __future__ import annotations

import sys

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow


def run(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    QGuiApplication.setApplicationName("legoart")
    win = MainWindow()
    win.show()
    return app.exec()
