@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
if defined PYTHONPATH (
  set "PYTHONPATH=%CD%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%CD%"
)
python -m hylyre bootstrap mock %*
exit /b %ERRORLEVEL%
