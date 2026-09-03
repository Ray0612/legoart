"""共享 fixtures。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:  # 兜底：确保能 import legoart
    sys.path.insert(0, str(SRC))

CURATED_DIR = REPO_ROOT / "data" / "catalog" / "curated"


@pytest.fixture(scope="session")
def curated_dir() -> Path:
    assert CURATED_DIR.is_dir(), f"缺少精选目录: {CURATED_DIR}"
    return CURATED_DIR


@pytest.fixture(scope="session")
def catalog(curated_dir):
    from legoart.catalog import Catalog

    return Catalog.from_dir(curated_dir)
