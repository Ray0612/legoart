"""后台工作线程：把耗时的 api.generate_plan 移出 UI 线程。"""

from __future__ import annotations

import io

from PyQt6.QtCore import QThread, pyqtSignal

from legoart import api
from legoart.errors import LegoArtError
from legoart.model import ImageSpec


class GenerationWorker(QThread):
    progress = pyqtSignal(str, float)  # stage, 0..1
    finished_ok = pyqtSignal(object)   # MosaicPlan
    failed = pyqtSignal(str)           # 错误文案（含错误码）

    def __init__(self, image_png: bytes, spec: ImageSpec, parent=None) -> None:
        super().__init__(parent)
        self._image_png = image_png
        self._spec = spec

    def run(self) -> None:
        try:
            plan = api.generate_plan(
                io.BytesIO(self._image_png), self._spec, progress=self._progress
            )
            self.finished_ok.emit(plan)
        except LegoArtError as e:
            self.failed.emit(str(e))
        except Exception as e:  # 未预期
            self.failed.emit(f"[ERR_UNKNOWN] {e}")

    def _progress(self, stage: str, frac: float) -> None:
        self.progress.emit(stage, frac)
