@echo off
rem PyRov one-click setup - double-click this file.
rem It runs setup.ps1 next to it (the repository is private, so the scripts
rem cannot be fetched from GitHub without signing in: download the project ZIP
rem from the repository page, extract it and run this file from that folder).
setlocal
if exist "%~dp0setup.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
) else (
    echo setup.ps1 was not found next to setup.bat.
    echo Download the project with Code ^> Download ZIP on GitHub, extract it,
    echo and run setup.bat from inside the extracted folder.
    pause
    exit /b 1
)
if errorlevel 1 pause
