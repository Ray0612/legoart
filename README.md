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

> 状态：M4 完成 —— 库存系统：SQLite DAO（原子增/减/扣减+历史快照）、Excel 导入导出、
> 库存约束三策略求解（精确 / 同形近似色 / 可铺缩拆分替代，CIEDE2000 最近色），
> 桌面库存管理对话框 + 库存模式向导 + “确认拼搭→扣减并记录历史”。119 项测试全绿。
