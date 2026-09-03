"""领域模型：纯数据对象（dataclass），零计算逻辑。

对象同时驱动：预览画布 / Excel / PDF / 库存扣减（见技术方案 §5）。
"""

from .bom import BomItem, BomModel
from .grid import GridModel
from .image_spec import ImageSpec, ShortageStrategy, StyleKind
from .layers import Layer, LayerStack
from .placements import PartPlacement
from .plan import MosaicPlan, SolverResult
from .regions import Region, SaliencyMap

__all__ = [
    "BomItem",
    "BomModel",
    "GridModel",
    "ImageSpec",
    "ShortageStrategy",
    "StyleKind",
    "Layer",
    "LayerStack",
    "PartPlacement",
    "MosaicPlan",
    "SolverResult",
    "Region",
    "SaliencyMap",
]
