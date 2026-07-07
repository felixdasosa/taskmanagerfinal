@echo off
echo =========================================
echo   Pornire Server PRODUCȚIE - Aplicatie Taskuri
echo =========================================

:: 1. Curatenie: Opreste orice Caddy ramas blocat in fundal (pentru a elibera porturile)
echo Curatam procesele vechi...
taskkill /F /IM caddy.exe >nul 2>&1

:: 2. Navigheaza automat in folderul unde se afla fisierul .bat
cd /d "%~dp0"

:: 3. Porneste serverul Python (Waitress + Design) intr-o fereastra noua
echo Pornesc Waitress (Aplicatia Python)...
start "Aplicația Python - Waitress" cmd /k ".\venv\Scripts\activate && python run_prod.py"

:: 4. Porneste portarul (Caddy) in alta fereastra noua
echo Pornesc Caddy (Web Server)...
start "Portarul - Caddy" cmd /k ".\caddy.exe run"

echo.
echo Serverul a pornit! Lasa cele doua ferestre negre deschise.
pause