"""极简 i18n：核心包只提供 zh/en 文案字典（不引入 Qt 依赖）。

规则：错误一律走 errors.code，UI 用 ``t(code, lang)`` 取文案；
找不到 key 时原样返回 key，避免静默空文案。
"""

from __future__ import annotations

from typing import Final

_ZH: Final[dict[str, str]] = {
    "app.title": "乐高画作智能转换器",
    "ERR_COLOR_NO_MATCH": "存在大面积颜色无法匹配官方色，请调整输入或放大尺寸",
    "ERR_OVER_60S": "本地计算超过 60 秒上限，请降低分辨率或改用手动模式",
    "ERR_MODEL_MISSING": "AI 模型文件缺失，已降级为无凸起模式（可稍后在设置中下载）",
    "ERR_CATALOG_NOT_FOUND": "未找到内置零件/颜色目录，请检查安装完整性",
    "catalog.loaded": "目录已加载：{colors} 色 / {parts} 件（{version}）",
}

_EN: Final[dict[str, str]] = {
    "app.title": "LEGO Art Converter",
    "ERR_COLOR_NO_MATCH": "Large areas cannot match any official color; adjust input or increase size",
    "ERR_OVER_60S": "Local computation exceeded the 60s limit; lower resolution or retry",
    "ERR_MODEL_MISSING": "AI model file missing; degraded to no-relief mode (download in settings)",
    "ERR_CATALOG_NOT_FOUND": "Bundled part/color catalog not found; check installation",
    "catalog.loaded": "Catalog loaded: {colors} colors / {parts} parts ({version})",
}

_TABLES: Final[dict[str, dict[str, str]]] = {"zh": _ZH, "en": _EN}

LANGS: Final[tuple[str, ...]] = ("zh", "en")
DEFAULT_LANG: Final[str] = "zh"


def t(key: str, lang: str = DEFAULT_LANG, **fmt: object) -> str:
    table = _TABLES.get(lang, _ZH)
    text = table.get(key, key)
    if fmt:
        try:
            text = text.format(**fmt)
        except (KeyError, ValueError):  # 占位符与参数不匹配时原样返回
            pass
    return text
