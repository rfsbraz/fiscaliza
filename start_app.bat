@echo off
echo Starting Portuguese Parliament Data Analysis Application...
echo.
echo Backend Flask server will start on http://127.0.0.1:5000
echo Frontend React server will start on http://localhost:5173
echo.

:: Check if npm is installed
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed. Please install Node.js first.
    pause
    exit /b 1
)

:: Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed. Please install Python first.
    pause
    exit /b 1
)

echo Starting servers...
echo.

:: Start both servers using concurrently
if exist "node_modules\concurrently" (
    npm run dev
) else (
    echo Installing dependencies first...
    npm install
    echo.
    echo Now starting servers...
    npm run dev
)

pause