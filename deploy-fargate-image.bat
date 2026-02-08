@echo off
REM Deploy Docker image for ECS Fargate (not Lambda)
REM This builds and pushes a standard Flask application image

echo ============================================================================
echo Building and Pushing Parliament App Docker Image for ECS Fargate
echo ============================================================================

set ECR_REGISTRY=715763094766.dkr.ecr.eu-west-1.amazonaws.com
set IMAGE_NAME=parliament-app

REM Generate unique timestamp tag for proper versioning
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "IMAGE_TAG=%YYYY%%MM%%DD%-%HH%%Min%%Sec%"

echo Using unique image tag: %IMAGE_TAG%

echo.
echo [1/5] Logging into ECR...
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin %ECR_REGISTRY%
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to login to ECR
    exit /b 1
)

echo.
echo [2/5] Building Docker image...
docker build -t %IMAGE_NAME%:%IMAGE_TAG% .
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to build Docker image
    exit /b 1
)

echo.
echo [3/5] Tagging image for ECR...
docker tag %IMAGE_NAME%:%IMAGE_TAG% %ECR_REGISTRY%/%IMAGE_NAME%:%IMAGE_TAG%
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to tag Docker image
    exit /b 1
)

echo.
echo [4/5] Pushing image to ECR...
docker push %ECR_REGISTRY%/%IMAGE_NAME%:%IMAGE_TAG%
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to push Docker image
    exit /b 1
)

echo.
echo [5/5] Updating Terraform variables...
REM Update the backend_image variable in terraform.tfvars
powershell -Command "(Get-Content terraform\terraform.tfvars) -replace 'backend_image = \".*\"', 'backend_image = \"%ECR_REGISTRY%/%IMAGE_NAME%:%IMAGE_TAG%\"' | Set-Content terraform\terraform.tfvars"

REM Also create temp file for compatibility
echo backend_image = "%ECR_REGISTRY%/%IMAGE_NAME%:%IMAGE_TAG%" > temp_backend_image.tfvars

echo.
echo ============================================================================
echo SUCCESS: Docker image built and pushed successfully!
echo ============================================================================
echo.
echo Image URI: %ECR_REGISTRY%/%IMAGE_NAME%:%IMAGE_TAG%
echo Image Tag: %IMAGE_TAG%
echo.
echo Updated terraform\terraform.tfvars with new image URI
echo.
echo Next step: Run 'terraform apply' to deploy the new image
echo ============================================================================

pause