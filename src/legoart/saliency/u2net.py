"""U²-Net 显著性适配器（TorchScript 接口）。

约定：模型输入为 ``(1,3,320,320)`` 归一化 [0,1] RGB，输出取 ``d1`` 分支
（原始尺寸 HxW），经 sigmoid + 双线性上采样回输入分辨率。

说明：直接放 U²-Net 的 .pth(state_dict) 需要同时携带网络结构；
为保持核心包轻量与可移植，本适配器接收**导出的 TorchScript 模型**
（``scripts/export_u2net_ts.py`` 可从 xuebinqin/U-2-Net 的 ``u2netp`` 导出）。
模型缺失时系统自动使用内置对比度显著性（resolve_provider 降级）。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


class TorchScriptSaliency:
    kind = "u2net"

    def __init__(self, model_path: str | Path, size: int = 320) -> None:
        import torch  # 延迟导入：无 torch 时不拖累核心包

        self.size = size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = torch.jit.load(str(model_path), map_location=self.device)
        self.model.eval()

    def predict(self, rgb: np.ndarray) -> np.ndarray:
        import cv2
        import torch

        arr = np.asarray(rgb, dtype=np.float32)
        img = cv2.resize(arr, (self.size, self.size), interpolation=cv2.INTER_AREA) / 255.0
        t = torch.from_numpy(img.transpose(2, 0, 1))[None]  # (1,3,320,320)
        t = t.to(self.device)
        with torch.no_grad():
            out = self.model(t)
        d1 = out["d1"] if isinstance(out, dict) else out[0]
        d1 = torch.sigmoid(d1)[0, 0].float().cpu().numpy()  # 0..1
        return cv2.resize(d1, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
