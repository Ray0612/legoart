"""Palette —— 官方色库内存视图：装载、Lab 缓存、最近色匹配。

匹配管线（技术方案 §6.1）：CIEDE2000 全距阵 + argmin；
大网格场景在此之上加 CIE76 粗筛 top-K（预留 ``coarse_topk`` 参数）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..catalog.models import ColorSpec
from .ciede2000 import delta_e00_pairwise
from .convert import rgb_to_lab


@dataclass(frozen=True, slots=True)
class ColorRecord:
    """Palette 内部条目（轻量，含索引无关字段）。"""

    color_id: str
    name_bl: str
    name_tlg: str
    rgb: tuple[int, int, int]
    is_trans: bool = False
    material: str = "solid"
    recommended: bool = True


class Palette:
    """不可变色板。``nearest`` 接受 (M,3) RGB(0..255) 查询并返回最近 color_id。"""

    def __init__(self, specs: list[ColorSpec]) -> None:
        self._records: dict[str, ColorRecord] = {}
        for s in specs:
            r = ColorRecord(
                color_id=s.color_id,
                name_bl=s.name_bl,
                name_tlg=s.name_tlg,
                rgb=s.rgb,
                is_trans=s.is_trans,
                material=s.material,
                recommended=s.recommended,
            )
            if r.color_id in self._records:
                raise ValueError(f"重复颜色 key: {r.color_id}")
            self._records[r.color_id] = r
        self._ids: tuple[str, ...] = tuple(self._records.keys())
        self._rgb: np.ndarray = np.array([self._records[i].rgb for i in self._ids], dtype=np.uint8)
        self._lab: np.ndarray = rgb_to_lab(self._rgb.astype(np.float64))
        self._recommended_idx: np.ndarray = np.array(
            [self._records[i].recommended for i in self._ids], dtype=bool
        )

    # ---- 只读视图 ----
    @property
    def ids(self) -> tuple[str, ...]:
        return self._ids

    @property
    def rgb(self) -> np.ndarray:
        """(N,3) uint8，与 ids 对齐。"""
        return self._rgb

    @property
    def lab(self) -> np.ndarray:
        """(N,3) float64 Lab，与 ids 对齐。"""
        return self._lab

    def __len__(self) -> int:
        return len(self._ids)

    def __contains__(self, color_id: str) -> bool:
        return color_id in self._records

    def get(self, color_id: str) -> ColorRecord | None:
        return self._records.get(color_id)

    @property
    def recommended_ids(self) -> tuple[str, ...]:
        return tuple(i for i in self._ids if self._records[i].recommended)

    # ---- 最近色匹配 ----
    def nearest(
        self,
        query_rgb: np.ndarray,
        *,
        color_set: str = "recommended",
    ) -> tuple[np.ndarray, np.ndarray]:
        """查询 (M,3) RGB(0..255) → (ids[M], de00[M])。

        color_set: "recommended" 仅常用色 / "all" 全色 / 显式 color_id 列表。
        """
        q = np.asarray(query_rgb, dtype=np.float64)
        if q.ndim == 1:
            q = q[None, :]
        if q.shape[-1] != 3:
            raise ValueError(f"query_rgb 最后一维须为 3，got {q.shape}")

        mask: np.ndarray
        if color_set == "recommended":
            mask = self._recommended_idx
        elif color_set == "all":
            mask = np.ones(len(self._ids), dtype=bool)
        else:  # 显式列表
            keys = list(color_set)
            missing = [k for k in keys if k not in self._records]
            if missing:
                raise ValueError(f"未知颜色: {missing}")
            mask = np.array([k in keys for k in self._ids], dtype=bool)

        idx = np.flatnonzero(mask)
        sub_lab = self._lab[idx]
        q_lab = rgb_to_lab(q)
        de = delta_e00_pairwise(q_lab, sub_lab)  # (M, len(idx))
        best = np.argmin(de, axis=1)
        ids = np.array([self._ids[idx[i]] for i in best], dtype=object)
        return ids, de[np.arange(len(q)), best]
