# 乐高画作智能转换器 · legoart

> 把任意图片转换成「乐高积木拼搭方案」的开源工具 —— 自动配色、生成物料清单与分层拼搭说明书。
> Turn any picture into a LEGO mosaic building plan: color matching, BOM, and layered instructions.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

<!-- 建仓后把 OWNER 换成你的用户名，启用 CI 徽章：
[![CI](https://github.com/OWNER/legoart/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/legoart/actions/workflows/ci.yml)
-->

## 功能特性

- **色块化转换**：采样（均值/中值去噪）→ CIEDE2000 色差量化到乐高官方色板，支持「常用色 / 全部色」候选集。
- **自动色调映射**：按色域对 Lab 亮度重映射，明显降低暗部偏差（`auto_tone`，强度可调）。
- **艺术海报风格**：按图片在官方色板内选取最优子集（12/24/40 色），适合人像/插画。
- **同色板件合并**：行优先贪心合并，输出更少、更大的板件（更快更好拼）。
- **显著性凸起 & 浮雕分层**：重点区域可轻微抬高，生成多层堆叠方案。
- **物料清单导出**：Excel（按层数量、RGB 色卡、缺件/替代表）＋ **PDF 分层拼搭说明书**（矢量网格、内嵌中文字体）。
- **库存系统**：SQLite 库存、Excel 导入导出、带缺件策略与替代规则的约束求解。
- **拍照识别入库**：Lab + k-means 色块分割识别已有积木（可选接入 YOLO/Ultralytics，自动降级）。
- **桌面客户端**：PyQt6 向导式流程（导入裁剪 → 参数与生成 → 分层预览 → 导出），支持离屏测试。

> 核心算法库（`legoart`）为纯 Python、零 UI 依赖，可被桌面端或未来的 Web 端复用。

## 快速开始

```bash
# 需要 Python 3.11+
pip install -e .                 # 仅核心算法库
pip install -e ".[desktop]"      # 加装 PyQt6 桌面客户端
pip install -e ".[ml]"           # 可选：显著性/识别的 torch 依赖（体积大，建议按需）
```

Windows 用户装好 `.[desktop]` 后，可直接双击仓库根目录的 `run_desktop.bat` 启动图形界面。

## 用法

**命令行（CLI）**

```bash
# 48 studs 宽、常用色集，输出方案 JSON 与预览图
python -m legoart.cli generate --image photo.jpg --width 48 --color-set recommended \
    --out plan.json --preview mosaic.png

# 用物理尺寸：宽 30cm（约 8mm/stud）
python -m legoart.cli generate --image photo.jpg --width 30 --unit cm

# 顺便导出 Excel 物料清单与 PDF 分层说明书
python -m legoart.cli generate --image photo.jpg --width 48 --excel bom.xlsx --pdf guide.pdf
```

**图形界面（GUI）**

```bash
python -m legoart_desktop        # 或双击 run_desktop.bat
```

示例方案文件见 [`examples/plan.example.json`](examples/plan.example.json)。

## 项目结构

```
src/legoart          # 核心算法库（纯 Python，零 UI 依赖）
  color/ mosaic/ model/ export/ inventory/ detect/ saliency/ storage/ ...
src/legoart_desktop  # PyQt6 桌面客户端
data/catalog         # 精选色库与零件目录（离线可用）
data/notices         # 第三方数据/代码许可声明
docs/                # 需求文档、决策记录、技术方案与架构设计
scripts/             # 目录构建、模型下载等辅助脚本
tests/               # 单元测试与冒烟测试
```

## 开发与测试

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev,desktop]"

pytest -q            # 运行测试（桌面端测试默认离屏 QT_QPA_PLATFORM=offscreen）
ruff check .         # 代码检查
```

当前进度：里程碑 **M0–M7 已完成**（脚手架 → 色块链路 → 板件合并/浮雕 → 桌面向导 → 库存系统 → 导出 → 拍照入库 → 艺术海报风格），约 **148 项测试全绿**。路线图与设计详见 [`docs/技术方案与架构设计.md`](docs/技术方案与架构设计.md)。

## 数据与第三方许可

色库与零件目录位于 `data/catalog/`，来源与许可证逐条登记在
[`data/notices/THIRD_PARTY_NOTICES.md`](data/notices/THIRD_PARTY_NOTICES.md)，其中权威色板快照来自
[zed0/lego-colour-matcher](https://github.com/zed0/lego-colour-matcher)（MIT），详见
[`data/catalog/vendor/LICENSE_zed0.txt`](data/catalog/vendor/LICENSE_zed0.txt)。

> **免责声明：** LEGO® 是 LEGO Group 的注册商标。本项目为非官方开源项目，与 LEGO Group 无任何隶属或授权关系。
> 颜色 RGB 为社区通行的近似值，乐高官方并不公布精确 RGB，请以实物为准。

## 参与贡献

欢迎提交 Issue 与 Pull Request！开始之前请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)（分支与提交规范、PR 流程、测试要求）；
参与本项目即表示同意遵守 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

- 需求与决策背景：[`docs/乐高生图项目文档.md`](docs/乐高生图项目文档.md)、[`docs/乐高生图项目_需求决策记录.md`](docs/乐高生图项目_需求决策记录.md)
- 技术方案与架构：[`docs/技术方案与架构设计.md`](docs/技术方案与架构设计.md)

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
