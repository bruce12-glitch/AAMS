@echo off
title AAMS local prototype
powershell.exe -NoLogo -NoProfile -File "%~dp0deploy\showcase-windows.ps1" -SkipTelegram
if errorlevel 1 (
    echo.
    echo AAMS could not start. Read the error above. Docker Desktop must be running.
    pause
    exit /b 1
)
echo.
echo AAMS keeps running in Docker Desktop. You can close this window.
pause
