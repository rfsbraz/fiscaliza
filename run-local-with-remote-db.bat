@echo off
REM Run local Flask app connected to remote PostgreSQL database
REM This allows testing the same data and schema as production

echo ============================================================================
echo Running Local Flask App with Remote PostgreSQL Database
echo ============================================================================

REM Get database credentials from Terraform
echo [1/3] Getting remote database connection details...
cd terraform
for /f "tokens=*" %%i in ('terraform output -raw rds_endpoint') do set DB_HOST=%%i
for /f "tokens=*" %%i in ('terraform output -raw rds_port') do set DB_PORT=%%i
for /f "tokens=*" %%i in ('terraform output -raw database_name') do set DB_NAME=%%i
cd ..

echo Database Host: %DB_HOST%
echo Database Port: %DB_PORT%
echo Database Name: %DB_NAME%

REM Set environment variables for local development with remote DB
echo.
echo [2/3] Setting up environment variables...
set FLASK_ENV=development
set FLASK_DEBUG=1
set DATABASE_URL=postgresql://fiscaliza_user:[GET_PASSWORD_FROM_SECRETS_MANAGER]@%DB_HOST%:%DB_PORT%/%DB_NAME%
set DATABASE_SECRET_ARN=arn:aws:secretsmanager:eu-west-1:715763094766:secret:fiscaliza-prod-db-credentials-2025-08-21-1531-bvx1hv
set AWS_DEFAULT_REGION=eu-west-1

REM Note: You'll need AWS credentials configured (aws configure or environment variables)
echo.
echo IMPORTANT: Make sure you have AWS credentials configured to access Secrets Manager
echo The app will fetch the database password from AWS Secrets Manager automatically
echo.

REM Start the Flask application
echo [3/3] Starting Flask application...
cd app
python main.py

pause