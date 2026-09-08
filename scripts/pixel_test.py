"""像素风转换测试工具（不含乐高颜色限制）。

作用：把指定图片直接降采样为 W×H 的"像素画"并原色直出 PNG 到桌面/指定路径，
用于隔离验证：采样与细节还原本身好不好（不经过乐高官方色匹配）。

用法：
  python scripts/pixel_test.py --image 路径 --width 96 [--cell 12] [--no-grid] [--out 输出.png]
不带参数时：默认输入 tmp/1 (209).jpg、宽度 96，输出到桌面 pixel_test_W96.png。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image, ImageDraw  # noqa: E402

from legoart.mosaic.sampling import sample_grid  # noqa: E402


def desktop() -> Path:
    return Path.home() / "Desktop"


def pixelize(image_path: str | Path, width: int, cell: int = 12, grid: bool = True) -> Path:
    im = Image.open(image_path).convert("RGB")
    height = max(1, round(width * im.height / im.width))
    t0 = time.perf_counter()
    cells = sample_grid(im, width, height, median_ksize=0)  # 平均色，无中值、无调色
    dt = (time.perf_counter() - t0) * 1000

    canvas = Image.new("RGB", (width * cell, height * cell), (20, 20, 24))
    d = ImageDraw.Draw(canvas)
    for y in range(height):
        for x in range(width):
            r, g, b = cells[y, x]
            d.rectangle(
                [x * cell, y * cell, (x + 1) * cell - 1, (y + 1) * cell - 1],
                fill=(int(round(r)), int(round(g)), int(round(b))),
            )
    if grid:
        col = (40, 40, 45)
        for i in range(width + 1):
            xx = i * cell
            d.line([(xx, 0), (xx, height * cell)], fill=col)
        for j in range(height + 1):
            yy = j * cell
            d.line([(0, yy), (width * cell, yy)], fill=col)

    out = desktop() / f"pixel_test_W{width}.png"
    canvas.save(out)
    print(
        f"OK: 输入 {im.width}x{im.height} -> 网格 {width}x{height} "
        f"(采样 {dt:.0f}ms)，原色直出（无乐高限制）"
    )
    print(f"输出: {out}")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", default=r"tmp/1 (209).jpg", help="输入图片路径")
    p.add_argument("--width", type=int, default=96, help="网格宽(studs/格数)")
    p.add_argument("--cell", type=int, default=12, help="每格输出像素(便于查看)")
    p.add_argument("--no-grid", action="store_true", help="不画格线")
    p.add_argument("--out", default=None, help="输出路径（默认桌面 pixel_test_W{width}.png）")
    args = p.parse_args(argv)
    if not Path(args.image).exists():
        print(f"[错误] 找不到图片: {args.image}", file=sys.stderr)
        return 1
    pixelize(
        args.image,
        args.width,
        cell=args.cell,
        grid=not args.no_grid,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
