@echo off
echo Starting ClassVision ERP Platform...
start cmd /k "cd server && node index.js"
timeout /t 2 >nul
start http://localhost:5000/login.html
