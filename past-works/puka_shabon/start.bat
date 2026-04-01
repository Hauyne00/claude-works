@echo off
cd /d "%~dp0"

C:\Python314\python.exe -m pip install pygame-ce pyttsx3 -q 2>nul

C:\Python314\python.exe puka_shabon.py

if %errorlevel% neq 0 (
    echo.
    echo Error: failed to start. Press any key.
    pause > nul
)
