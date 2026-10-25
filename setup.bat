@echo off
rem PyRov one-click setup - double-click this file.
rem It runs setup.ps1 next to it, or downloads it from GitHub if it is not there.
setlocal
if exist "%~dp0setup.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/buggYateer/robotics-project/main/setup.ps1 | iex"
)
if errorlevel 1 pause
