@echo off
title Deploy SaulGPT Frontend to Firebase Hosting
echo ========================================================
echo   SAULGPT - FIREBASE HOSTING DEPLOYMENT
echo ========================================================
echo.

cd /d "%~dp0saulgpt-ui"
echo [1/3] Building production bundle...
call npm.cmd run build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b %ERRORLEVEL%
)

cd /d "%~dp0"
echo.
echo [2/3] Checking Firebase Authentication...
call npx.cmd --yes firebase-tools login
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Firebase login failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Deploying to Firebase Hosting...
call npx.cmd --yes firebase-tools deploy --only hosting
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Deployment failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo   DEPLOYMENT SUCCESSFUL!
echo   Your live web app URL is displayed above.
echo ========================================================
pause
