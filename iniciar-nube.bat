@echo off
title Nimbus Cloud - Mi Nube Personal
echo ============================================================
echo   Iniciando Nimbus Cloud en http://localhost:3000 ...
echo ============================================================
start http://localhost:3000
if exist "C:\Users\Jose Daniel Connor\AppData\Local\Programs\Python\Python313\python.exe" (
    "C:\Users\Jose Daniel Connor\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0server.py"
) else (
    python "%~dp0server.py"
)
pause
