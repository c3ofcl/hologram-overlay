@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
    py -m pip install PySide6
    py hologram_overlay.py
) else (
    python -m pip install PySide6
    python hologram_overlay.py
)
pause
