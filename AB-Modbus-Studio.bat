@echo off
cd /d "%~dp0"
python -m ab_modbus
if errorlevel 1 pause
