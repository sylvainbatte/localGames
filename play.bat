@echo off
python "%~dp0play.py" %*
if errorlevel 1 python3 "%~dp0play.py" %*
