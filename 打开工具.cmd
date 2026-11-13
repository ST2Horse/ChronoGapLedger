@echo off
cd /d "%~dp0"
python chronogapledger.py --gui
if errorlevel 1 pause
