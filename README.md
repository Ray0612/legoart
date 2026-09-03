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

> 状态：M3 完成 —— PyQt6 桌面壳三页向导（导入+鼠标框选裁剪 → 尺寸/单位/色集/
> 显著性参数+后台线程生成 → 分层预览+统计+保存方案 JSON）。离屏测试覆盖裁剪数学、
> 页面流程、worker 线程、主窗口端到端。共 98 项测试全绿。
>
> 启动：`.venv\Scripts\python -m legoart_desktop`（需真实显示器）。
