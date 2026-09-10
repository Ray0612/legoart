# 贡献指南 · Contributing to legoart

感谢你愿意参与！本文说明开发环境、分支与提交规范、PR 流程和测试要求。

## 环境准备

```bash
git clone https://github.com/Ray0612/legoart.git
cd legoart
python -m venv .venv
# Windows: .\.venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev,desktop]"
```

可选：需要显著性（saliency）或拍照识别（detect）的 AI 能力时，再安装 `pip install -e ".[ml]"`
（torch 体积较大，非必需；未安装时会自动降级到传统算法）。

## 分支与提交

- 保护分支为 `main`，**不要直接向 `main` push**，一律走 Pull Request。
- 每个改动开一个短命分支：`feat/xxx`、`fix/xxx`、`docs/xxx`、`refactor/xxx`。
- 提交信息建议采用 [Conventional Commits](https://www.conventionalcommits.org/)：
  `feat: 新增海报风格色集选择`、`fix: 修正暗部色调映射`、`docs: 补充 CLI 示例`。中英文均可。
- 一次 PR 聚焦一件事，避免混杂无关改动与格式化噪声。

## Pull Request 流程

1. 从最新 `main` 拉分支：`git switch main && git pull && git switch -c feat/xxx`
2. 完成改动，跑通测试与 lint（见下）。
3. 推送并开 PR：`git push -u origin feat/xxx`，在 PR 中说明**改了什么、为什么、怎么测**。
4. 通过 CI（GitHub Actions）与至少 1 位维护者 Review 后合并（建议 Squash merge）。
5. 合并后删除该分支。

分支落后 `main` 时优先变基自己的功能分支：`git fetch origin && git rebase origin/main`
（只对未被他人拉取的**自己的**分支变基 / force-push；用 `--force-with-lease` 而非 `--force`）。

## 代码风格与测试

- 代码风格由 [ruff](https://docs.astral.sh/ruff/) 负责：提交前运行 `ruff check .`（CI 也会跑）。
- 新增/修改功能请补充测试，保持测试全绿：`pytest -q`。
- 桌面端测试使用离屏模式，无需真实显示器（`QT_QPA_PLATFORM=offscreen`，CI 已配置）。
- 保持核心库 `legoart` 纯 Python、零 UI 依赖；桌面/未来的 Web 端只通过 `legoart.api` 复用。

## 数据集 / 色库变更

`data/catalog/` 是随包发布的精选数据。

- **不要手工大规模改色值**：口径统一后由 `scripts/build_curated_catalog.py` 生成维护。
- 颜色/零件的增删改请同时更新版本号（`catalog_version`）并在 PR 中说明来源。
- 引入任何第三方数据、模型或代码，请在 [`data/notices/THIRD_PARTY_NOTICES.md`](data/notices/THIRD_PARTY_NOTICES.md)
  登记其来源与许可证。上游色板数据为 MIT（见 `data/catalog/vendor/LICENSE_zed0.txt`）。

## 报告问题

- Bug 与功能建议请用 Issue 模板提交，尽量附上复现步骤、输入图片特征、参数与期望结果。
- 请注意：本项目与 LEGO Group 无隶属关系，请勿在 Issue 中要求使用官方未公开数据。

## 许可

贡献的代码将以本项目的 [MIT License](LICENSE) 授权发布。
