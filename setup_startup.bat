@echo off
REM Registers DISHA to launch silently (no console window) EVERY time you
REM log into Windows, permanently, until you remove it. Uses Task Scheduler
REM so you never have to manually run "python main.py" again.
REM Run this file once, as your normal user (no admin needed).

set TASK_NAME=DISHA_Assistant
set SCRIPT_DIR=%~dp0
set PYTHONW=%SCRIPT_DIR%venv\Scripts\pythonw.exe
set MAIN_SCRIPT=%SCRIPT_DIR%main.py

REM --- Sanity check: make sure the venv actually exists before registering ---
if not exist "%PYTHONW%" (
    echo.
    echo ERROR: Could not find %PYTHONW%
    echo Make sure you already ran:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo before running this script.
    echo.
    pause
    exit /b 1
)

REM Remove any previous registration first, so re-running this is always safe
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

schtasks /Create /TN "%TASK_NAME%" ^
  /TR "\"%PYTHONW%\" \"%MAIN_SCRIPT%\"" ^
  /SC ONLOGON ^
  /RL LIMITED ^
  /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo  DISHA is now PERMANENT.
    echo  She will launch silently every time you log
    echo  into Windows - no terminal, no manual start.
    echo ============================================
    echo.
    echo To verify: open Task Scheduler ^(taskschd.msc^) and
    echo look for "%TASK_NAME%" under Task Scheduler Library.
    echo.
    echo To turn this OFF later:
    echo   schtasks /Delete /TN "%TASK_NAME%" /F
) else (
    echo.
    echo Something went wrong registering the task. Try running
    echo this .bat file as Administrator ^(right-click - Run as administrator^).
)
echo.
pause
