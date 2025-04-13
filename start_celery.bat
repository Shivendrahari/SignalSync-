@echo off
cd /d %~dp0
set PYTHONPATH=%cd%
celery -A myproject worker -l info -P solo