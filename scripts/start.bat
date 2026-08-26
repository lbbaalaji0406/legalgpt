@echo off
title SaulGPT - Indian Legal Intelligence
color 0a
set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.19.0-win-x64;%USERPROFILE%\.local\bin;%PATH%"

echo ═══════════════════════════════════════════
echo   SaulGPT - Starting All Services
echo ═══════════════════════════════════════════
echo.

set "REPO_DIR=%~dp0.."
set "VENV_PYTHON=%REPO_DIR%\.venv\Scripts\python.exe"

REM Start backend in background
start "SaulGPT - Backend" cmd /k "cd /d %REPO_DIR%\backend && "%VENV_PYTHON%" api_server.py"

REM Wait a moment for backend to start
timeout /t 4 /nobreak >nul

REM Start frontend
start "SaulGPT - Frontend" cmd /k "cd /d %REPO_DIR%\saulgpt-ui && npm run dev"

echo ═══════════════════════════════════════════
echo   SaulGPT is running!
echo.
echo   Backend API:  http://localhost:8000
echo   Frontend:    http://localhost:5173
echo.
echo   Press any key to exit this window...
echo ═══════════════════════════════════════════
pause >nul