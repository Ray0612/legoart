"""Catalog 目录测试：精选数据装载、去重、搜索、报错。"""

import json

import pytest

from legoart.catalog import Catalog
from legoart.errors import CatalogError


def test_from_dir_counts(catalog, curated_dir):
    assert len(catalog.colors) > 0
    assert len(catalog.parts) > 0
    white = catalog.color("White")
    assert white is not None
    assert white.rgb == (255, 255, 255)
    assert catalog.color("Red").rgb[0] > 150  # 红分量高


def test_plates_present(catalog):
    p3024 = catalog.part("3024")
    assert p3024 is not None and p3024.stud_area == 1
    p3020 = catalog.part("3020")
    assert p3020 is not None and p3020.stud_area == 8
    plates = catalog.plate_candidates()
    assert plates and plates[0].stud_area == 1
    areas = [p.stud_area for p in plates]
    assert areas == sorted(areas)


def test_search(catalog):
    hits = catalog.search_parts("3020")
    assert hits and hits[0].design_id == "3020"
    hits = catalog.search_parts("plate 2 x 4", limit=5)
    assert any(p.design_id == "3020" for p in hits)
    assert catalog.search_parts("zzz-no-such") == []
    tiles = catalog.search_parts(family="tile")
    assert tiles and all(p.shape_family == "tile" for p in tiles)


def test_missing_dir_raises(tmp_path):
    with pytest.raises(CatalogError):
        Catalog.from_dir(tmp_path / "nope")


def test_duplicate_color_raises(tmp_path):
    d = tmp_path / "cur"
    d.mkdir()
    colors = [
        {"color_id": "Red", "name_bl": "Red", "rgb": "#C91A09"},
        {"color_id": "Red", "name_bl": "Red2", "rgb": "#C91A09"},
    ]
    (d / "colors.json").write_text(json.dumps(colors), encoding="utf-8")
    (d / "parts_plates.json").write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(CatalogError):
        Catalog.from_dir(d)


def test_bad_hex_raises():
    from legoart.catalog.models import ColorSpec

    with pytest.raises(ValueError):
        ColorSpec("X", "X", "", "#GGGGGG").rgb
