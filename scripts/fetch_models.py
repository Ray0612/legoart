"""模型权重下载（可选）：显著性 U²-Net / 检测 YOLO。

用法：
  python scripts/fetch_models.py saliency-ts --url <saliency.pt 下载地址> [--out data/models/saliency.pt]
  python scripts/fetch_models.py yolo       --url <yolov8n.pt ...>        [--out data/models/yolov8n.pt]

说明：
- 默认不自动下载（体积/网络/许可证由用户自持，见 data/notices/THIRD_PARTY_NOTICES.md）；
- saliency.pt 须为 TorchScript 导出的 U²-Netp（见 scripts/export_u2net_ts.py 说明，
  该导出脚本需在 xuebinqin/U-2-Net 仓库环境下运行一次）；
- 未提供权重时程序自动使用内置对比度显著性并给出提示（不阻塞主流程）。
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parents[1] / "data" / "models"


def _download(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}\n  -> {out}")
    tmp = out.with_suffix(out.suffix + ".part")
    try:
        urllib.request.urlretrieve(url, tmp)  # noqa: S310 (用户显式指定 URL)
        tmp.replace(out)
        print("done")
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"下载失败: {e}") from e


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fetch_models", description=__doc__)
    sub = p.add_subparsers(dest="what", required=True)
    for name in ("saliency-ts", "yolo"):
        sp = sub.add_parser(name)
        sp.add_argument("--url", required=True)
        sp.add_argument("--out", default=None)
        sp.set_defaults(name=name)
    args = p.parse_args(argv)
    default_file = "saliency.pt" if args.what == "saliency-ts" else "yolo.pt"
    out = Path(args.out) if args.out else (DEFAULT_DIR / default_file)
    _download(args.url, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
