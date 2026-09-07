"""ImageSpec —— 一次生成的完整参数快照（可序列化，写入 project_history）。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class StyleKind(str, Enum):
    """风格轴（D2/D8）：首版只实现 COLOR_BLOCK，TEXTURE 第二迭代。"""

    COLOR_BLOCK = "color_block"  # 色块化
    TEXTURE = "texture"          # 纹理保留（二期）


class ShortageStrategy(str, Enum):
    """库存缺货三策略（D13）。"""

    APPROXIMATE = "approximate"  # 近似替代：库存最近似颜色替换
    MISSING_LIST = "missing_list"  # 生成缺件清单：保留原色
    EXTREME = "extreme"          # 极限拼搭：只用库存，缺处留空/黑白灰


@dataclass(slots=True)
class ImageSpec:
    """一次"生成方案"的用户参数（与坐标系约定：col=x 向右，row=y 向下）。"""

    grid_w: int = 0                       # studs 宽（列数）
    grid_h: int = 0                       # studs 高（行数，由宽/裁剪比自动补全 D4）
    style: StyleKind = StyleKind.COLOR_BLOCK
    use_inventory: bool = False           # 需求轴：False=理想购物车 / True=库存约束
    shortage_strategy: ShortageStrategy = ShortageStrategy.MISSING_LIST
    saliency_enabled: bool = True         # 是否做 AI 重点识别（D6）
    saliency_max_raise: int = 3           # AI 区域凸起层高上限（用户可调 1..6+）
    color_set: str = "recommended"        # 候选色集: recommended|all（见 palette）
    input_unit: str = "studs"             # 用户原始输入单位 studs|cm（D10）
    catalog_version: str = ""             # 生成时目录版本（快照一致性 §8.2）
    params_extra: dict = field(default_factory=dict)  # 预留扩展

    def to_dict(self) -> dict:
        d = asdict(self)
        d["style"] = self.style.value
        d["shortage_strategy"] = self.shortage_strategy.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ImageSpec":
        data = dict(data)
        data["style"] = StyleKind(data.get("style", StyleKind.COLOR_BLOCK.value))
        data["shortage_strategy"] = ShortageStrategy(
            data.get("shortage_strategy", ShortageStrategy.MISSING_LIST.value)
        )
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
