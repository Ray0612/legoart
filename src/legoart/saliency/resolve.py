"""Provider 解析：AI 权重(可下载/自带) 优先，否则内置对比度显著性。

- 权重文件位置：``LEGOART_SALIENCY_MODEL`` 环境变量，或
  ``data/models/saliency.pt``（TorchScript，见 scripts/fetch_models.py 说明）。
- 返回 ``(provider, used_ai: bool)``；无权重且无 torch 时不抛错，
  由调用方把"已降级"作为 warning 提示（ERR_MODEL_MISSING）。
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import SaliencyProvider
from .contrast import ContrastSaliency


def _default_model_path() -> Path | None:
    env = os.environ.get("LEGOART_SALIENCY_MODEL")
    if env:
        return Path(env)
    # 仓库 data/models 或运行目录 data/models
    here = Path(__file__).resolve()
    repo = here.parents[3] / "data" / "models" / "saliency.pt"
    cwd = Path.cwd() / "data" / "models" / "saliency.pt"
    for p in (repo, cwd):
        if p.exists():
            return p
    return None


def resolve_provider() -> tuple[SaliencyProvider, bool]:
    """返回 (provider, used_ai)。AI 权重缺失或不可加载 → 内置对比度 + used_ai=False。"""
    model_path = _default_model_path()
    if model_path is not None:
        try:
            from .u2net import TorchScriptSaliency

            return TorchScriptSaliency(model_path), True
        except Exception:
            pass  # 模型加载失败 → 降级
    return ContrastSaliency(), False
