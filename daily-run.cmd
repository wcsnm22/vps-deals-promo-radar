@echo off
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
python daily.py >> "%~dp0data\daily-run.log" 2>&1
