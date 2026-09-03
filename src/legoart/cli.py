"""命令行入口（M1 冒烟）：python -m legoart.cli generate ...

示例：
  python -m legoart.cli generate --image photo.jpg --width 48 --color-set recommended \
      --out plan.json --preview mosaic.png
  python -m legoart.cli generate --image photo.jpg --width 30 --unit cm   # 宽 30cm → studs
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

from . import api, __version__
from .errors import LegoArtError
from .model import ImageSpec
from .model.image_spec import StyleKind

STUD_CM = 0.8  # 1 stud ≈ 8mm（D10）


def _cm_to_studs(cm: float) -> int:
    return max(1, round(cm / STUD_CM))


def _render_preview(grid, palette, out: Path, cell_px: int = 20) -> None:
    """用色库 RGB 渲染网格为 PNG（cell_px=每格像素）。"""
    import numpy as np

    h, w = grid.height, grid.width
    canvas = Image.new("RGB", (w * cell_px, h * cell_px), (20, 20, 20))
    px = canvas.load()
    for y in range(h):
        for x in range(w):
            rgb = palette.rgb_of(grid.colors[y, x]) or (0, 0, 0)
            for dy in range(cell_px):
                for dx in range(cell_px):
                    px[x * cell_px + dx, y * cell_px + dy] = rgb
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")


def _cmd_generate(args) -> int:
    if args.unit == "cm":
        grid_w = _cm_to_studs(args.width)
    else:
        grid_w = int(args.width)
    if grid_w < 1:
        print("[ERR_DATA] 宽度换算后为 0 studs", file=sys.stderr)
        return 1

    spec = ImageSpec(
        grid_w=grid_w,
        grid_h=int(args.height) if args.height else 0,  # 0 → 按比例自动补全
        style=StyleKind.COLOR_BLOCK,
        use_inventory=False,
        color_set=args.color_set,
        input_unit=args.unit,
    )

    plan = api.generate_plan(args.image, spec)
    print(
        f"grid {plan.grid.width}x{plan.grid.height} studs, "
        f"{plan.grid.width * plan.grid.height} cells, "
        f"{len(set(plan.grid.colors.ravel()))} colors, "
        f"elapsed {plan.elapsed_ms} ms"
    )

    counts: Counter[str] = Counter(plan.grid.colors.ravel().tolist())
    pal = api.build_palette()
    for cid, n in counts.most_common(12):
        rec = pal.get(cid)
        name = rec.name_bl if rec else cid
        print(f"  {name:20s} {n:5d} cells")
    if plan.warnings:
        for wmsg in plan.warnings:
            print(f"WARN {wmsg}", file=sys.stderr)

    out = Path(args.out) if args.out else Path("plan.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"plan -> {out}")

    if args.preview:
        prev = Path(args.preview)
        _render_preview(plan.grid, pal, prev)
        print(f"preview -> {prev}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="legoart", description="LEGO Art Converter (M1)")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="生成色块化方案")
    g.add_argument("--image", required=True, help="输入图片路径")
    g.add_argument("--width", type=float, required=True, help="宽度（数值，单位见 --unit）")
    g.add_argument("--height", type=float, default=None, help="高度；缺省按图片比例自动")
    g.add_argument("--unit", choices=("studs", "cm"), default="studs", help="宽度单位")
    g.add_argument(
        "--color-set", choices=("recommended", "all"), default="recommended",
        help="候选色集（recommended=常用色）",
    )
    g.add_argument("--out", default=None, help="方案 JSON 输出路径（默认 ./plan.json）")
    g.add_argument("--preview", default=None, help="可选：输出网格预览 PNG 路径")
    g.set_defaults(func=_cmd_generate)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except LegoArtError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:  # 未预期错误
        print(f"[ERR_UNKNOWN] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
