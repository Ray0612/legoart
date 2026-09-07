@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 乐高画作智能转换器 (LEGO Art Converter)...
if not exist ".venv\Scripts\python.exe" (
  echo [错误] 未找到 .venv，请先执行: python -m venv .venv 并安装依赖
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m legoart_desktop
if errorlevel 1 pause
