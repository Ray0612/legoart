"""马赛克网格视图：按层渲染色格（顶视），格间细线。"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from legoart.color import Palette
from legoart.model import GridModel


class MosaicView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._grid: GridModel | None = None
        self._palette: Palette | None = None
        self._empty_color = QColor(40, 40, 45)
        self.setMinimumSize(240, 240)

    def set_content(self, grid: GridModel | None, palette: Palette | None) -> None:
        self._grid = grid
        self._palette = palette
        self.update()

    def paintEvent(self, _) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(25, 25, 28))
        g = self._grid
        if g is None:
            painter.setPen(QPen(QColor(150, 150, 150)))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "（暂无网格）")
            return
        w, h = g.width, g.height
        cell = max(2.0, min(self.width() / w, self.height() / h))
        gw, gh = w * cell, h * cell
        ox = (self.width() - gw) / 2
        oy = (self.height() - gh) / 2
        for y in range(h):
            for x in range(w):
                cid = g.colors[y, x]
                color = QColor(30, 30, 32)
                if cid:
                    rgb = self._palette.rgb_of(cid) if self._palette else None
                    color = QColor(*rgb) if rgb else QColor(90, 90, 95)
                painter.fillRect(QRectF(ox + x * cell, oy + y * cell, cell, cell), color)
        # 格线
        painter.setPen(QPen(QColor(0, 0, 0, 70)))
        for i in range(w + 1):
            x = ox + i * cell
            painter.drawLine(int(x), int(oy), int(x), int(oy + gh))
        for j in range(h + 1):
            y = oy + j * cell
            painter.drawLine(int(ox), int(y), int(ox + gw), int(y))
