"""裁剪画布：显示原图、鼠标框选裁剪区域（D4：成品比例 = 裁剪比例）。"""

from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import QWidget


def pil_to_qimage(pil: Image.Image) -> QImage:
    rgb = pil.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    img = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return img.copy()  # 持有独立数据


class CropCanvas(QWidget):
    """鼠标拖拽框选。坐标均以*原图*像素计（缩放只在绘制层）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source: QImage | None = None
        self._start: QPointF | None = None
        self._current: QPointF | None = None
        self._rect: QRect | None = None  # 原图坐标（非空表示已有选择）
        self.setMinimumSize(420, 320)
        self.setMouseTracking(True)

    # ---- 外部接口 ----
    def set_image(self, pil: Image.Image) -> None:
        self._source = pil_to_qimage(pil)
        self._rect = None
        self._start = self._current = None
        self.update()

    def has_image(self) -> bool:
        return self._source is not None

    def clear_selection(self) -> None:
        self._rect = None
        self._start = self._current = None
        self.update()

    def selection_rect(self) -> QRect | None:
        """返回原图坐标系下的选择矩形；未选择返回 None（调用方决定是否视为整幅）。"""
        return QRect(self._rect) if self._rect else None

    def set_selection(self, rect: QRect) -> None:
        """程序化设置选择（测试/键盘微调用）。rect 为原图坐标。"""
        self._rect = QRect(rect)
        self.update()

    def aspect_ratio(self) -> float:
        """当前裁剪宽高比（宽/高）；无选择=整幅。"""
        img = self._source
        if img is None or img.width() == 0 or img.height() == 0:
            return 1.0
        if self._rect and self._rect.width() > 0 and self._rect.height() > 0:
            return self._rect.width() / self._rect.height()
        return img.width() / img.height()

    # ---- 事件 ----
    def mousePressEvent(self, e) -> None:
        if not self._source:
            return
        pos = self._to_image(e.position())
        self._start = pos
        self._current = pos
        self.update()

    def mouseMoveEvent(self, e) -> None:
        if self._start is not None and self._source:
            self._current = self._to_image(e.position())
            self.update()

    def mouseReleaseEvent(self, e) -> None:
        if self._start is not None and self._current is not None:
            self._commit_selection()
        self._start = self._current = None
        self.update()

    def _commit_selection(self) -> None:
        if not self._source:
            return
        p1 = self._start.toPoint()
        p2 = self._current.toPoint()
        if p1 == p2:
            return
        r = QRect(p1, p2).normalized().intersected(self._source.rect())
        if r.width() < 2 or r.height() < 2:
            return
        self._rect = r

    def _to_image(self, p: QPointF) -> QPointF:
        """widget 坐标 → 原图坐标。"""
        img, fit = self._fit_rect()
        if fit.width() <= 0:
            return QPointF(0, 0)
        return QPointF(
            (p.x() - fit.x()) * img.width() / fit.width(),
            (p.y() - fit.y()) * img.height() / fit.height(),
        )

    def _fit_rect(self) -> tuple[QRectF, QRectF]:
        """返回 (图片整幅, 适合绘制区域)。"""
        img = self._source
        if img is None:
            return QRectF(), QRectF(self.rect())
        area = self.rect()
        scale = min(area.width() / img.width(), area.height() / img.height())
        w = img.width() * scale
        h = img.height() * scale
        x = (area.width() - w) / 2
        y = (area.height() - h) / 2
        return QRectF(0, 0, img.width(), img.height()), QRectF(x, y, w, h)

    # ---- 绘制 ----
    def paintEvent(self, _) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(35, 35, 40))
        if self._source is None:
            painter.setPen(QPen(QColor(170, 170, 170)))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "打开图片后在此框选裁剪区域")
            return
        _, fit = self._fit_rect()
        painter.drawImage(fit, self._source)
        if self._rect is None and self._start is not None and self._current is not None:
            r = self._to_fit_rect(QRectF(self._start, self._current))
            self._paint_sel(painter, r)
        elif self._rect is not None:
            self._paint_sel(painter, self._to_fit_rect(QRectF(self._rect)))

    def _to_fit_rect(self, r: QRectF) -> QRectF:
        img, fit = self._fit_rect()
        if img.width() <= 0:
            return QRectF()
        return QRectF(
            fit.x() + r.x() * fit.width() / img.width(),
            fit.y() + r.y() * fit.height() / img.height(),
            r.width() * fit.width() / img.width(),
            r.height() * fit.height() / img.height(),
        )

    def _paint_sel(self, painter: QPainter, fit_r: QRectF) -> None:
        sel = fit_r.normalized().intersected(QRectF(self.rect()))
        if sel.isEmpty():
            return
        painter.fillRect(QRectF(self.rect()), QColor(0, 0, 0, 90))
        painter.fillRect(sel, QColor(255, 255, 255, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.drawImage(sel, self._source, self._source_region_for(sel))
        pen = QPen(QColor(255, 235, 60))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(sel)
        label = f"{sel.width():.0f} x {sel.height():.0f} px"
        painter.setPen(QColor(255, 235, 60))
        painter.drawText(QPoint(int(sel.left() + 6), int(max(sel.top() - 6, 14))), label)

    def _source_region_for(self, sel: QRectF) -> QRectF:
        img, fit = self._fit_rect()
        return QRectF(
            (sel.x() - fit.x()) * img.width() / fit.width(),
            (sel.y() - fit.y()) * img.height() / fit.height(),
            sel.width() * img.width() / fit.width(),
            sel.height() * img.height() / fit.height(),
        )
