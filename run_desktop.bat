@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] venv not found. Run: python -m venv .venv
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -X utf8 -m legoart_desktop > ui.log 2>&1
if errorlevel 1 (
  echo.
  echo App exited with error. See ui.log
  pause
)
