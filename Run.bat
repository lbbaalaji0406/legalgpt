@echo off
title SaulGPT - Legal Intelligence Platform
color 0a
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

:: Define directories
set "ROOT_DIR=%~dp0"
set "VENV_PYTHON=%ROOT_DIR%.venv\Scripts\python.exe"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%saulgpt-ui"

:: Add Node.js and local bins to PATH if installed via Winget
set "NODE_WINGET=%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.19.0-win-x64"
if exist "%NODE_WINGET%" (
    set "PATH=%NODE_WINGET%;%PATH%"
)
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

cls
echo ===============================================
echo        SAULGPT - LEGAL INTELLIGENCE
echo ===============================================
echo.
echo  [1] Start SaulGPT (Backend + Frontend)
echo  [2] Setup (Install Python and Node Dependencies)
echo  [3] Exit
echo.
choice /c 123 /n /m "Select option (1-3): "

if errorlevel 3 goto :eof
if errorlevel 2 goto setup
if errorlevel 1 goto start

:start
cls
echo ===============================================
echo  Launching SaulGPT Services...
echo ===============================================
echo.

:: Verify virtual environment exists
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at:
    echo         "%VENV_PYTHON%"
    echo.
    echo Please run Option [2] Setup first to configure the environment.
    echo.
    pause
    goto :eof
)

:: 1. Start Backend in its own window with correct working directory
echo [1/2] Starting FastAPI Backend on port 8000...
start "SaulGPT-Backend" cmd /k "cd /d "%BACKEND_DIR%" && title SaulGPT-Backend && "%VENV_PYTHON%" api_server.py"

:: Non-blocking wait for backend to bind port 8000
echo Waiting for Backend to initialize...
ping -n 5 127.0.0.1 >nul

:: 2. Start Frontend in its own window
echo [2/2] Starting Vite Frontend on port 5173...
start "SaulGPT-Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && title SaulGPT-Frontend && npm.cmd run dev"

:: Non-blocking wait for Vite dev server
echo Waiting for Frontend to initialize...
ping -n 4 127.0.0.1 >nul

:: 3. Open the UI in default browser
echo.
echo Opening browser: http://localhost:5173
start http://localhost:5173

echo.
echo ===============================================
echo   SaulGPT is running!
echo   Frontend UI:  http://localhost:5173
echo   Backend API:  http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo ===============================================
echo.
echo Leave the backend and frontend terminal windows open.
echo Close them whenever you want to stop SaulGPT.
echo.
pause
goto :eof

:setup
cls
echo ===============================================
echo  Setting up SaulGPT Environment
echo ===============================================
echo.

:: Check Python venv
if not exist "%VENV_PYTHON%" (
    echo Creating Python virtual environment...
    python -m venv "%ROOT_DIR%.venv"
)

echo Installing Backend requirements...
"%VENV_PYTHON%" -m pip install --upgrade pip
"%VENV_PYTHON%" -m pip install -r "%BACKEND_DIR%\requirements.txt"

echo.
echo Installing Frontend node_modules...
cd /d "%FRONTEND_DIR%"
call npm.cmd install
cd /d "%ROOT_DIR%"

echo.
echo ===============================================
echo  Setup complete! You can now start SaulGPT.
echo ===============================================
echo.
pause
goto :eof