@echo off
rem Launch minibeamng.py with a double click.
rem The script will ask you to paste the path to your BeamNG.drive folder.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found on this system.
    echo Install it from https://www.python.org/downloads/ and tick "Add Python to PATH".
    pause
    exit /b 1
)

python "%~dp0minibeamng.py" %*
echo.
pause
