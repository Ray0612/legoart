"""重建精选色库（O5）：以 Rebrickable 全量颜色快照为权威，替换/扩充 curated colors.json。

数据：data/catalog/vendor/rebrickable_colors_2019.json
  （zed0/lego-colour-matcher 的 Rebrickable API 响应快照，MIT，含色名/RGB/is_trans/映射）

规则：
- 匹配集 = "普通实色"（非 Trans/Chrome/Pearl/Metallic/Flat/Speckle/Glitter/Modulex/
  Vintage/Glow/Milky/Metal- 等特殊面漆），这是拼搭马赛克会用的砖色；
- 对 curated 中原有但快照未收录的色（如 Nougat 系列现代命名）做回退保留；
- recommended（“常用色”）= 旧 curated 标过 recommended 的色名 ∪ 补充常用名；
- 结果写回 data/catalog/curated/colors.json（schema 不变）。

用法：python scripts/build_curated_catalog.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "data" / "catalog" / "vendor" / "rebrickable_colors_2019.json"
CURATED = ROOT / "data" / "catalog" / "curated" / "colors.json"

_FINISH_RE = re.compile(
    r"^(trans|chrome|pearl|metallic|flat |speckle|glitter|modulex|vintage|glow|milky|metal\b|foil)",
    re.I,
)
_BAD_TOKENS = ("ink",)


def _normal_solid(name: str, is_trans: bool) -> bool:
    if is_trans or _FINISH_RE.match(name):
        return False
    return not any(t in name.lower() for t in _BAD_TOKENS)


def _tlg_code(entry: dict) -> str:
    ext = entry.get("external_ids") or {}
    lego = ext.get("LEGO") or {}
    descrs = lego.get("ext_descrs") or []
    for d in descrs:
        if d and d[0]:
            return d[0]
    return ""


def main() -> int:
    raw = json.loads(VENDOR.read_text(encoding="utf-8"))
    results = raw["results"] if isinstance(raw, dict) else raw

    old = json.loads(CURATED.read_text(encoding="utf-8"))
    rec_names = {c["color_id"] for c in old if c.get("recommended", True)}
    old_by_id = {c["color_id"]: c for c in old}

    # 1) 快照普通实色
    out: dict[str, dict] = {}
    for e in results:
        if not _normal_solid(str(e.get("name", "")), bool(e.get("is_trans"))):
            continue
        rgb = str(e.get("rgb", "000000")).lstrip("#").upper()
        cid = str(e["name"])
        out[cid] = {
            "color_id": cid,
            "name_bl": cid,
            "name_tlg": _tlg_code(e),
            "rgb": f"#{rgb}",
            "is_trans": False,
            "material": "solid",
            "recommended": cid in rec_names,
            "refs": {"rebrickable_id": e.get("id")},
        }
    # 2) curated 回退（快照缺失的现代命名色）
    for cid, c in old_by_id.items():
        if cid not in out:
            out[cid] = {
                "color_id": cid,
                "name_bl": c["name_bl"],
                "name_tlg": c.get("name_tlg", ""),
                "rgb": c["rgb"],
                "is_trans": False,
                "material": "solid",
                "recommended": cid in rec_names,
                "refs": {"curated_fallback": True},
            }
    # 3) 补充常见"常用色"标记（若快照里存在）
    extra_rec = {
        "White", "Light Bluish Gray", "Dark Bluish Gray", "Black", "Red", "Dark Red",
        "Orange", "Dark Orange", "Yellow", "Bright Green", "Green", "Dark Green",
        "Blue", "Dark Blue", "Medium Azure", "Dark Azure", "Purple", "Magenta",
        "Pink", "Light Bluish Green", "Tan", "Light Nougat", "Reddish Brown",
        "Dark Brown", "Medium Nougat", "Nougat", "Olive Green", "Sand Green",
        "Lime", "Medium Green", "Dark Turquoise", "Light Turquoise", "Medium Blue",
        "Sky Blue", "Light Blue", "Light Gray", "Dark Gray", "Very Light Bluish Gray",
        "Dark Tan", "Sand Blue", "Sand Purple", "Sand Red", "Light Pink", "Medium Lavender",
        "Lavender", "Bright Light Blue", "Bright Light Yellow", "Bright Light Orange",
        "Yellowish Green", "Coral", "Rust",
    }
    for cid in extra_rec:
        if cid in out:
            out[cid]["recommended"] = True

    final = sorted(out.values(), key=lambda c: c["color_id"])
    CURATED.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_rec = sum(1 for c in final if c["recommended"])
    print(f"colors.json 已重建：{len(final)} 色（推荐 {n_rec}）；源 {VENDOR.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
