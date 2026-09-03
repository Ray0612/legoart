"""中文字体注册（ReportLab）。本地生成 PDF 用系统字体；缺失时回退 Helvetica。"""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_CANDIDATES: list[tuple[str, Path, int]] = [
    # (注册名, 路径, TTC 子字体索引)
    ("CNFont", Path("C:/Windows/Fonts/msyh.ttc"), 0),      # 微软雅黑
    ("CNFont", Path("C:/Windows/Fonts/msyhbd.ttc"), 0),
    ("CNFont", Path("C:/Windows/Fonts/simhei.ttf"), 0),    # 黑体
    ("CNFont", Path("C:/Windows/Fonts/simsun.ttc"), 0),    # 宋体
]

_font_name: str | None = None


def register_cn_font() -> str:
    """注册中文字体并返回可用字体名；失败返回 'Helvetica'（中文将显示为方块）。"""
    global _font_name
    if _font_name is not None:
        return _font_name
    for name, path, idx in _FONT_CANDIDATES:
        try:
            pdfmetrics.registerFont(TTFont(name, str(path), subfontIndex=idx))
            _font_name = name
            return name
        except Exception:
            continue
    _font_name = "Helvetica"
    return _font_name


def cn_font() -> str:
    return register_cn_font()
