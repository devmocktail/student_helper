@echo off
rem Launch the new PySide6 StudyHelper from this folder.
cd /d %~dp0
python -m app.main
if errorlevel 1 pause
