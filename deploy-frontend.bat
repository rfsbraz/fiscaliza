@echo off
REM Deploy Frontend to S3 Static Website
REM This script builds and deploys the frontend application

echo ============================================================================
echo Building and Deploying Frontend to S3
echo ============================================================================

REM Get S3 bucket name from Terraform outputs
echo [1/6] Getting S3 bucket name from Terraform...
cd terraform
for /f "tokens=*" %%i in ('terraform output -raw s3_bucket_name') do set BUCKET_NAME=%%i
for /f "tokens=*" %%i in ('terraform output -raw api_url') do set API_URL=%%i
cd ..

echo S3 Bucket: %BUCKET_NAME%
echo API URL: %API_URL%

echo.
echo [2/6] Installing frontend dependencies...
cd frontend
call npm install
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

echo.
echo [3/6] Using existing production environment configuration...
REM Use existing .env.production file (contains VITE_API_URL=https://api.fiscaliza.pt)
if exist .env.production (
    echo Found .env.production - using existing configuration
    type .env.production
) else (
    echo Creating .env.production with API endpoint...
    echo REACT_APP_API_URL=%API_URL% > .env.production
    echo VITE_API_BASE_URL=%API_URL%/api >> .env.production
)

echo.
echo [4/6] Building frontend application...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to build frontend
    exit /b 1
)

echo.
echo [5/6] Deploying to S3...
REM Deploy index.html with no-cache headers for cache busting
aws s3 cp dist/index.html s3://%BUCKET_NAME%/index.html --cache-control "no-cache, no-store, must-revalidate" --metadata-directive REPLACE
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to upload index.html
    exit /b 1
)

REM Sync remaining files with standard caching
aws s3 sync dist/ s3://%BUCKET_NAME%/ --delete --exclude "*.map" --exclude "index.html" --cache-control "public, max-age=31536000"
if %ERRORLEVEL% neq 0 (
    aws s3 sync build/ s3://%BUCKET_NAME%/ --delete --exclude "*.map" --exclude "index.html" --cache-control "public, max-age=31536000"
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to deploy to S3
        exit /b 1
    )
)

echo.
echo [6/6] Invalidating CloudFront cache...
cd ..\terraform
for /f "tokens=*" %%i in ('terraform output -raw website_url') do set WEBSITE_URL=%%i
for /f "tokens=*" %%i in ('terraform output -raw cloudfront_distribution_id') do set CLOUDFRONT_ID=%%i
cd ..

REM Invalidate CloudFront cache if distribution exists
if "%CLOUDFRONT_ID%" neq "CloudFront not enabled" (
    echo Invalidating CloudFront distribution: %CLOUDFRONT_ID%
    aws cloudfront create-invalidation --distribution-id %CLOUDFRONT_ID% --paths "/*" --region us-east-1
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to invalidate CloudFront cache, but deployment was successful
    ) else (
        echo CloudFront cache invalidated successfully
    )
) else (
    echo CloudFront not enabled, skipping cache invalidation
)

echo.
echo ============================================================================
echo SUCCESS: Frontend deployed successfully!
echo ============================================================================
echo.
echo Website URL: %WEBSITE_URL%
echo API URL: %API_URL%
echo S3 Bucket: %BUCKET_NAME%
echo.
echo Next steps:
echo 1. Test the website: %WEBSITE_URL%
echo 2. Test API connectivity from the frontend
echo 3. Check CloudFlare cache settings if needed
echo ============================================================================

pause