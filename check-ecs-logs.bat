@echo off
REM Check ECS CloudWatch Logs for Parliament Application
REM This script fetches recent logs from the ECS Fargate service

echo ============================================================================
echo Checking ECS Fargate CloudWatch Logs
echo ============================================================================

set LOG_GROUP=/ecs/fiscaliza-prod/backend
set REGION=eu-west-1

echo.
echo Log Group: %LOG_GROUP%
echo Region: %REGION%
echo.

echo [1/3] Getting log streams...
aws logs describe-log-streams --log-group-name %LOG_GROUP% --region %REGION% --order-by LastEventTime --descending --max-items 5 --query "logStreams[*].{StreamName:logStreamName,LastEvent:lastEventTime}" --output table

echo.
echo [2/3] Getting latest log stream...
for /f "tokens=*" %%i in ('aws logs describe-log-streams --log-group-name %LOG_GROUP% --region %REGION% --order-by LastEventTime --descending --max-items 1 --query "logStreams[0].logStreamName" --output text') do set LATEST_STREAM=%%i

echo Latest stream: %LATEST_STREAM%

echo.
echo [3/3] Fetching recent logs...
echo ============================================================================
echo RECENT LOGS (Last 50 lines):
echo ============================================================================

aws logs get-log-events --log-group-name %LOG_GROUP% --log-stream-name %LATEST_STREAM% --region %REGION% --start-from-head --query "events[-50:].message" --output text

echo.
echo ============================================================================
echo STREAMING LIVE LOGS (Press Ctrl+C to stop):
echo ============================================================================

aws logs tail %LOG_GROUP% --follow --region %REGION%