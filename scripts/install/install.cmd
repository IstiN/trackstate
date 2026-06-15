@echo off
REM TrackState CLI installer for Windows Command Prompt.
REM
REM Usage:
REM   curl -sSL https://github.com/IstiN/trackstate/releases/latest/download/install.cmd -o install.cmd
REM   install.cmd
REM
REM   install.cmd v1.2.3

setlocal enabledelayedexpansion

set "VERSION=%~1"
if "%~1"=="" set "VERSION=latest"

if /I "%VERSION%"=="latest" (
    set "SCRIPT_URL=https://github.com/IstiN/trackstate/releases/latest/download/install.ps1"
) else (
    set "SCRIPT_URL=https://github.com/IstiN/trackstate/releases/download/%VERSION%/install.ps1"
)

set "TEMP_SCRIPT=%TEMP%\trackstate-install-%RANDOM%.ps1"

echo --> Downloading TrackState installer...
curl -sSL --fail "%SCRIPT_URL%" -o "%TEMP_SCRIPT%"
if errorlevel 1 (
    echo ERROR: Failed to download installer from %SCRIPT_URL%
    exit /b 1
)

echo --> Running TrackState installer...
powershell.exe -ExecutionPolicy Bypass -NoProfile -Command "& '%TEMP_SCRIPT%' '%VERSION%'"
set "EXIT_CODE=%ERRORLEVEL%"

del /f /q "%TEMP_SCRIPT%" >nul 2>&1

exit /b %EXIT_CODE%
