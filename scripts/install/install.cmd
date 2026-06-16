@echo off
REM TrackState CLI installer for Windows Command Prompt.
REM
REM Usage:
REM   curl -fsSL https://github.com/IstiN/trackstate/releases/latest/download/install.cmd -o install.cmd
REM   install.cmd
REM
REM   install.cmd v1.2.3
REM   install.cmd -Force
REM   install.cmd v1.2.3 -Force

setlocal enabledelayedexpansion

set "VERSION=%~1"
set "FORCE_FLAG=%~2"
if "%~1"=="" set "VERSION=latest"
if /I "%~1"=="-Force" (
    set "VERSION=latest"
    set "FORCE_FLAG=-Force"
)

if /I "%VERSION%"=="latest" (
    set "SCRIPT_URL=https://github.com/__REPO_PLACEHOLDER__/releases/latest/download/install.ps1"
) else (
    set "SCRIPT_URL=https://github.com/__REPO_PLACEHOLDER__/releases/download/%VERSION%/install.ps1"
)

for /f "tokens=2 delims==" %%a in ('wmic process get ParentProcessId /value ^| find "="') do set "PPID=%%a"
for /f "tokens=1-4 delims=/: " %%a in ('echo %date% %time%') do set "TS=%%a%%b%%c%%d%%e%%f"
set "TEMP_SCRIPT=%TEMP%\trackstate-install-%RANDOM%-%PPID%-%TS%.ps1"

echo --> Downloading TrackState installer...
curl -fsSL --fail "%SCRIPT_URL%" -o "%TEMP_SCRIPT%"
if errorlevel 1 (
    echo ERROR: Failed to download installer from %SCRIPT_URL%
    exit /b 1
)

echo --> Running TrackState installer...
powershell.exe -ExecutionPolicy Bypass -NoProfile -Command "& '%TEMP_SCRIPT%' '%VERSION%' %FORCE_FLAG%"
set "EXIT_CODE=%ERRORLEVEL%"

del /f /q "%TEMP_SCRIPT%" >nul 2>&1

exit /b %EXIT_CODE%
