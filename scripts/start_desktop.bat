@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
  echo Bedrock virtual environment was not found.
  echo Run: python -m venv .venv ^&^& .venv\Scripts\activate ^&^& python -m pip install -e ".[dev,mcp,desktop]"
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
bedrock-desktop
if errorlevel 1 (
  echo.
  echo New QML desktop failed. Try: bedrock-desktop-legacy
  pause
)
