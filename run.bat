@echo off
title ClassVision Pro // Unified AI Surveillance & ERP Engine
cd /d "C:\Users\ls511\ClassVision"

echo ==============================================================
echo [1/3] Clearing stale processes on Port 5000...
echo ==============================================================
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1

echo ==============================================================
echo [2/3] Activating Virtual Environment and Starting Engine...
echo ==============================================================
start "" http://localhost:5000/faculty.html
.\venv\Scripts\python.exe ai-engine\cctv_scanner.py

pause
