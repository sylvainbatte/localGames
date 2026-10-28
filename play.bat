@echo off
setlocal
rem Essaie le lanceur "py", puis "python", puis "python3" (le premier qui fonctionne vraiment).
for %%P in ("py -3" python python3) do (
    %%~P -c "import sys" >/dev/null 2>&1 && (
        %%~P "%~dp0play.py" %*
        exit /b %errorlevel%
    )
)
echo Python 3.8+ est introuvable. Installe-le depuis https://www.python.org/downloads/ ^(coche "Add python.exe to PATH"^).
exit /b 1
