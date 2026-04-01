@echo off
cd /d "%~dp0"
echo === debug start === > debug_log.txt
echo. >> debug_log.txt

echo [1] Python path check >> debug_log.txt
C:\Python314\python.exe --version >> debug_log.txt 2>&1
echo errorlevel: %errorlevel% >> debug_log.txt
echo. >> debug_log.txt

echo [2] pygame-ce check >> debug_log.txt
C:\Python314\python.exe -c "import pygame; print(pygame.version.ver)" >> debug_log.txt 2>&1
echo errorlevel: %errorlevel% >> debug_log.txt
echo. >> debug_log.txt

echo [3] syntax check >> debug_log.txt
C:\Python314\python.exe -m py_compile puka_shabon.py >> debug_log.txt 2>&1
echo errorlevel: %errorlevel% >> debug_log.txt
echo. >> debug_log.txt

echo [4] launch game >> debug_log.txt
C:\Python314\python.exe puka_shabon.py >> debug_log.txt 2>&1
echo errorlevel after game: %errorlevel% >> debug_log.txt

echo. >> debug_log.txt
echo === debug end === >> debug_log.txt

echo Done. See debug_log.txt
pause
