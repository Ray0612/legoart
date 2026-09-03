# data/catalog/curated —— 精选目录（v0 说明）

## 数据性质与来源

- **colors.json**：BrickLink 色名为主键（`color_id`），TLG 乐高官方命名为辅。
  RGB 为社区通行的"乐高色近似值"（Rebrickable / BrickLink 色板口径）。
  ⚠️ **注意**：LEGO 官方从不公布精确 RGB；本表数值为 best-effort 近似，
  且 **尚未逐条经权威数据源校验**（对应开放项 O5/O11）。
- **parts_plates.json**：方案生成可用的矩形板件（含设计号与 studs 尺寸）。
- **parts_common.json**：库存录入高频件（砖/瓦/斜坡等）。

⚠️ **待办（数据里程碑）**：开发 `scripts/build_curated_catalog.py`，
以 Rebrickable `colors.csv`（RGB/材质/外部编号）+ legocolors（TLG 命名）
交叉生成并校验本目录；零件设计号须对照 Rebrickable `parts.csv` 复核
（本 v0 表部分 design_id 需人工确认，如 3070b/3069b/3068b 的 b 后缀）。

## 用法
- 不要手工大规模改色值：数值口径统一后由脚本维护；
- 颜色/零件的增删改走 git + 版本号（catalog_version）。
