@echo off
chcp 65001 >nul
cd /d D:\Files\Pycharm\guo
D:\Files\Anaconda_envs\envs\work\python.exe D:\Files\Pycharm\guo\main.py check >> D:\Files\Pycharm\guo\logs\daily_check.log 2>&1
