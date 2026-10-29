@echo off
chcp 65001 >nul
title 截屏取码自动粘贴工具
cd /d "%~dp0"
python code_paster.py
if errorlevel 1 pause
