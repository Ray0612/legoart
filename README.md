# 乐高画作智能转换器 (LEGO Art Converter)

把任意电子图片转换为"乐高积木拼搭方案"的工具（Windows 本地客户端）。

- 需求文档：[docs/乐高生图项目文档.md](docs/乐高生图项目文档.md)
- 决策记录：[docs/乐高生图项目_需求决策记录.md](docs/乐高生图项目_需求决策记录.md)
- 技术设计：[docs/技术方案与架构设计.md](docs/技术方案与架构设计.md)

## 仓库结构

```
src/legoart          # 核心算法库（纯 Python，零 UI 依赖，可被 Web 端复用）
src/legoart_desktop  # PyQt6 桌面客户端
data/catalog         # 精选目录数据（离线可用）
data/models          # 模型权重（gitignore，脚本下载）
tests                # 单元测试 / 冒烟
```

## 开发

```bash
# 1) 创建虚拟环境并安装依赖
python -m venv .venv

# 2) 依赖安装 / 运行（本机沙箱环境需以下两行环境变量）：
#    - TMP/TEMP 指向工作区内临时目录
#    - PYTHONPATH 注入 .bootstrap/sitecustomize.py（把 0o700 临时目录改为 0o777，
#      否则 ensurepip/pip/pytest 的临时文件会被沙箱拒绝写入）
$env:TMP = (Join-Path $PWD '.devtmp'); $env:TEMP = $env:TMP
$env:PYTHONPATH = (Join-Path $PWD '.bootstrap') + ';' + (Join-Path $PWD 'src')
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

> `venv` 内置的 ensurepip 子进程不吃 `PYTHONPATH`：若需重建 venv，
> 先 `python -m venv --without-pip .venv`，再手工执行
> `$env:PYTHONPATH=...; .\.venv\Scripts\python.exe -m ensurepip --upgrade --default-pip`。

> 状态：M5 完成 —— 导出：Excel BOM（颜色/RGB 色块/逐层用量/总用量 + 缺件/替代明细），
> PDF 分层说明书（封面预览 + 物料清单 + 每层 6 视角矢量图 + 中文嵌入字体）；
> api.export_plan / CLI --excel/--pdf / 预览页导出按钮。132 项测试全绿。
