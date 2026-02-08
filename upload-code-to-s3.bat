@echo off
REM Upload Parliament Code to S3 for Spot Instances
REM This script creates a code bundle and uploads it to S3

echo ============================================================================
echo Parliament Code Bundle Upload Script
echo ============================================================================
echo.

REM Get S3 bucket name from Terraform
echo [1/6] Getting S3 bucket name from Terraform...
cd terraform
for /f "tokens=*" %%i in ('terraform output -raw s3_bucket_name 2^>nul') do set BUCKET_NAME=%%i
cd ..

if "%BUCKET_NAME%"=="" (
    echo ERROR: Could not get S3 bucket name from Terraform
    echo Make sure Terraform is initialized and deployed
    pause
    exit /b 1
)

echo S3 Bucket: %BUCKET_NAME%
echo.

REM Clean up any existing bundle
echo [2/6] Cleaning up previous bundle...
if exist code-bundle rmdir /s /q code-bundle
if exist parliament-code.zip del parliament-code.zip

REM Create bundle directory structure
echo [3/6] Creating code bundle...
mkdir code-bundle\parliament

REM Copy essential directories
echo Copying scripts directory...
if exist scripts (
    xcopy scripts code-bundle\parliament\scripts /E /I /Q
) else (
    echo WARNING: scripts directory not found
)

echo Copying database directory (excluding backups)...
if exist database (
    REM Copy database structure but exclude backup files to save space
    xcopy database\*.py code-bundle\parliament\database\ /I /Q 2>nul
    if exist database\models xcopy database\models code-bundle\parliament\database\models /E /I /Q
    if exist database\migrations xcopy database\migrations code-bundle\parliament\database\migrations /E /I /Q
    echo Database files copied (backups excluded to save disk space)
) else (
    echo WARNING: database directory not found
)

REM Copy essential files
echo Copying configuration files...
if exist requirements.txt copy requirements.txt code-bundle\parliament\
if exist config.py copy config.py code-bundle\parliament\
if exist CLAUDE.md copy CLAUDE.md code-bundle\parliament\

REM Copy any config directories
if exist config xcopy config code-bundle\parliament\config /E /I /Q

REM Create __init__.py files for Python modules
echo Creating Python module files...
echo. > code-bundle\parliament\__init__.py
if exist code-bundle\parliament\scripts echo. > code-bundle\parliament\scripts\__init__.py
if exist code-bundle\parliament\scripts\data_processing echo. > code-bundle\parliament\scripts\data_processing\__init__.py
if exist code-bundle\parliament\scripts\data_processing\mappers echo. > code-bundle\parliament\scripts\data_processing\mappers\__init__.py
if exist code-bundle\parliament\database echo. > code-bundle\parliament\database\__init__.py

REM Create ZIP archive
echo [4/6] Creating ZIP archive...
cd code-bundle
powershell -Command "Compress-Archive -Path parliament -DestinationPath ..\parliament-code.zip -Force"
cd ..

if not exist parliament-code.zip (
    echo ERROR: Failed to create ZIP archive
    pause
    exit /b 1
)

REM Get file size
for %%A in (parliament-code.zip) do set FileSize=%%~zA
set /a FileSizeMB=%FileSize%/1024/1024

echo Archive created: parliament-code.zip (%FileSizeMB% MB)
echo.

REM Upload to S3
echo [5/6] Uploading to S3...
aws s3 cp parliament-code.zip s3://%BUCKET_NAME%/parliament-code.zip --metadata "created=%date%_%time%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to upload to S3
    echo Make sure AWS CLI is configured and you have S3 permissions
    pause
    exit /b 1
)

echo.
echo [6/6] Verifying upload...
aws s3 ls s3://%BUCKET_NAME%/parliament-code.zip

if %ERRORLEVEL% neq 0 (
    echo ERROR: Upload verification failed
    pause
    exit /b 1
)

REM Cleanup local files
echo.
echo Cleaning up local files...
rmdir /s /q code-bundle
del parliament-code.zip

echo.
echo ============================================================================
echo SUCCESS: Parliament code uploaded to S3!
echo ============================================================================
echo.
echo S3 Location: s3://%BUCKET_NAME%/parliament-code.zip
echo File Size: %FileSizeMB% MB
echo.
echo Your spot instances will now download the code from S3 when launched.
echo.
echo Next steps:
echo 1. Deploy updated Lambda function: terraform apply -target=aws_lambda_function.spot_launcher
echo 2. Test spot instance: curl -X POST [lambda-function-url]
echo 3. Monitor logs: aws logs tail /aws/parliament/import --follow
echo ============================================================================

pause