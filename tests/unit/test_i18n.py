"""i18n 与错误体系冒烟。"""

from legoart.errors import ColorError, LegoArtError, LegoArtTimeoutError
from legoart.i18n import t


def test_i18n_zh_and_en():
    zh = t("ERR_COLOR_NO_MATCH")
    en = t("ERR_COLOR_NO_MATCH", "en")
    assert zh != en and zh != "ERR_COLOR_NO_MATCH"
    assert "60" in t("ERR_OVER_60S")


def test_i18n_missing_key_fallback():
    assert t("NO_SUCH_KEY_XYZ") == "NO_SUCH_KEY_XYZ"


def test_error_hierarchy():
    e = ColorError("x")
    assert isinstance(e, LegoArtError)
    assert e.code == "ERR_COLOR"
    assert "ERR_COLOR" in str(e)
    assert issubclass(LegoArtTimeoutError, LegoArtError)
