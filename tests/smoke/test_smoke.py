"""冒烟：包可导入、API 装配可用、PyQt6 可实例化（offscreen）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_package_importable():
    import legoart

    assert legoart.__version__.startswith("0.1")
    from legoart.errors import CatalogError, LegoArtError, StorageError

    assert issubclass(CatalogError, LegoArtError)
    assert issubclass(StorageError, LegoArtError)


def test_api_load_catalog_and_palette():
    from legoart import api
    from legoart.color import Palette

    cat = api.load_catalog()
    assert len(cat.colors) > 0 and len(cat.parts) > 0
    pal = api.build_palette(cat)
    assert isinstance(pal, Palette)
    assert len(pal) == len(cat.colors)


def test_model_objects_roundtrip():
    import numpy as np

    from legoart.model import GridModel, ImageSpec, LayerStack, MosaicPlan
    from legoart.model.image_spec import ShortageStrategy, StyleKind

    g = GridModel(2, 1, np.array([["Red", "Blue"]], dtype=object))
    spec = ImageSpec(
        grid_w=2,
        grid_h=1,
        style=StyleKind.COLOR_BLOCK,
        use_inventory=True,
        shortage_strategy=ShortageStrategy.MISSING_LIST,
    )
    plan = MosaicPlan(spec=spec, grid=g)
    plan.bom.add("3024", "Red", 1, layer=0)
    d = plan.to_dict()
    assert d["grid"]["w"] == 2
    assert d["bom"][0]["design_id"] == "3024"
    assert d["spec"]["style"] == "color_block"

    ls = LayerStack(2, 1)
    ls.add(0, g)
    assert ls.height_total == 1


def test_pyqt6_smoke():
    from PyQt6.QtWidgets import QApplication, QLabel

    app = QApplication.instance() or QApplication([])
    label = QLabel("legoart")
    assert label.text() == "legoart"
    label.deleteLater()
