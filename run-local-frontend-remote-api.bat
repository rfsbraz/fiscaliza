@echo off
REM Run local React frontend connected to remote API
REM This allows testing frontend changes against production data

echo ============================================================================
echo Running Local React Frontend with Remote API
echo ============================================================================

REM Get API URL from Terraform
echo [1/3] Getting remote API endpoint...
cd terraform
for /f "tokens=*" %%i in ('terraform output -raw api_url') do set REMOTE_API_URL=%%i
cd ..

echo Remote API URL: %REMOTE_API_URL%

REM Create temporary .env.local for development with remote API
echo.
echo [2/3] Setting up frontend environment for remote API...
cd frontend

echo # Local development with remote API > .env.local
echo REACT_APP_API_URL=%REMOTE_API_URL% >> .env.local
echo VITE_API_BASE_URL=%REMOTE_API_URL%/api >> .env.local
echo. >> .env.local
echo # Development mode settings >> .env.local
echo VITE_NODE_ENV=development >> .env.local
echo REACT_APP_NODE_ENV=development >> .env.local

echo Created .env.local with remote API configuration
type .env.local

REM Install dependencies if needed
echo.
echo [3/4] Installing dependencies (if needed)...
if not exist node_modules (
    echo Installing npm dependencies...
    call npm install
)

REM Start the development server
echo.
echo [4/4] Starting React development server...
echo.
echo Frontend will run on: http://localhost:3000
echo Connected to remote API: %REMOTE_API_URL%
echo.
call npm run dev

REM Cleanup
echo.
echo Cleaning up temporary configuration...
del .env.local 2>nul

cd ..
pause