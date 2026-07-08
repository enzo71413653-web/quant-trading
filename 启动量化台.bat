@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   正在启动「我的量化学习台」...
echo   电脑上: 浏览器会自动打开 http://localhost:8501
echo   手机上: 连同一个 WiFi, 打开下面出现的 Network URL
echo   关闭:   在本窗口按 Ctrl+C, 或直接关掉窗口
echo ============================================
".venv\Scripts\streamlit.exe" run app.py
pause
