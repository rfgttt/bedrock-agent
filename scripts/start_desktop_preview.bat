@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
  echo Bedrock virtual environment was not found.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
bedrock-desktop-preview
if errorlevel 1 pause
