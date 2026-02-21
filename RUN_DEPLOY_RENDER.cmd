@echo off
cd /d "%~dp0"
echo Starting auto deploy setup...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\publish_to_render.ps1" -RepoUrl "https://github.com/Marwah273/marwah.git"
echo.
echo If you see any error, take a screenshot and send it to Copilot.
pause
