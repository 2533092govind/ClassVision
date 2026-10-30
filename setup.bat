@echo off
echo ====================================================
echo  ClassVision ERP & Biometric Attendance Setup
echo ====================================================
echo.
echo [1/2] Installing Node.js ERP backend dependencies...
cd server
call npm install
cd ..

echo.
echo [2/2] Setting up Python AI Virtual Environment...
cd ai-engine
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate
pip install opencv-python numpy requests insightface onnxruntime
cd ..

echo.
echo ====================================================
echo  Setup Completed Successfully! Run 'run.bat' to start.
echo ====================================================
pause
