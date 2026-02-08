# Launch Spot Instance and Watch Logs Script
# This script launches a spot instance and monitors its CloudWatch logs in real-time

param(
    [string]$OperationMode = "discovery"
)

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Parliament Spot Instance Launcher and Monitor" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Operation Mode: $OperationMode" -ForegroundColor Yellow
Write-Host ""

# Launch the spot instance
Write-Host "[1/4] Launching spot instance..." -ForegroundColor Green
$payload = @{
    mode = $OperationMode
} | ConvertTo-Json -Compress

Write-Host "Payload: $payload"

try {
    # Convert payload to base64
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $payloadBase64 = [System.Convert]::ToBase64String($payloadBytes)
    
    # Invoke Lambda with base64 payload
    $result = aws lambda invoke --function-name fiscaliza-prod-spot-launcher --payload $payloadBase64 response.json --region eu-west-1
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to launch spot instance"
    }
    
    Write-Host ""
    Write-Host "[2/4] Parsing response..." -ForegroundColor Green
    
    # Parse response
    $responseContent = Get-Content response.json | ConvertFrom-Json
    $responseBody = $responseContent.body | ConvertFrom-Json
    
    Write-Host "Response: $($responseBody | ConvertTo-Json -Depth 3)"
    
    $instanceId = $responseBody.instanceId
    $spotRequestId = $responseBody.spotRequestId
    
    if ($instanceId -eq $null -or $instanceId -eq "null" -or $instanceId -eq "") {
        Write-Host "WARNING: Instance ID not yet available. Checking spot request status..." -ForegroundColor Yellow
        Write-Host "Spot Request ID: $spotRequestId"
        Write-Host "Waiting for instance to be launched..."
        
        # Poll for instance ID
        for ($i = 1; $i -le 24; $i++) {
            Start-Sleep -Seconds 5
            
            $instanceIdResult = aws ec2 describe-spot-instance-requests --spot-instance-request-ids $spotRequestId --query "SpotInstanceRequests[0].InstanceId" --output text
            
            if ($instanceIdResult -ne "None" -and $instanceIdResult -ne "" -and $instanceIdResult -ne $null) {
                $instanceId = $instanceIdResult
                Write-Host "Instance launched: $instanceId" -ForegroundColor Green
                break
            }
            
            Write-Host "Attempt $i/24 - Still waiting for instance..." -ForegroundColor Yellow
        }
        
        if ($instanceId -eq $null -or $instanceId -eq "null" -or $instanceId -eq "" -or $instanceId -eq "None") {
            throw "Instance did not launch within 2 minutes"
        }
    }
    
    Write-Host ""
    Write-Host "[3/4] Instance ID: $instanceId" -ForegroundColor Green
    Write-Host ""
    
    # Wait for instance to start logging
    Write-Host "[4/4] Waiting for instance to start and begin logging..." -ForegroundColor Green
    Write-Host "This may take 1-2 minutes for the instance to boot and start the import process..."
    Write-Host ""
    
    # Check instance status
    Write-Host "Checking instance status..." -ForegroundColor Yellow
    try {
        $instanceStatus = aws ec2 describe-instances --instance-ids $instanceId --query "Reservations[0].Instances[0].State.Name" --output text --region eu-west-1
        Write-Host "Instance status: $instanceStatus" -ForegroundColor $(if ($instanceStatus -eq "running") { "Green" } else { "Yellow" })
        
        if ($instanceStatus -eq "terminated" -or $instanceStatus -eq "stopping" -or $instanceStatus -eq "stopped") {
            Write-Host "ERROR: Instance is $instanceStatus. Something went wrong during launch." -ForegroundColor Red
            throw "Instance failed to start properly"
        }
    } catch {
        Write-Host "Warning: Could not check instance status: $_" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Press Ctrl+C to stop watching logs" -ForegroundColor Yellow
    Write-Host ""
    
    Start-Sleep -Seconds 30
    
    # Start tailing logs
    Write-Host "=== SPOT INSTANCE LOGS ===" -ForegroundColor Cyan
    
    # Wait for log group to be created and logs to appear
    Write-Host "Waiting for log group to be created and logs to appear..." -ForegroundColor Yellow
    $logGroupExists = $false
    $maxWaitTime = 300 # 5 minutes
    $waitTime = 0
    
    while (-not $logGroupExists -and $waitTime -lt $maxWaitTime) {
        try {
            # Check if log group exists
            $logGroups = aws logs describe-log-groups --log-group-name-prefix "/aws/parliament/import" --region eu-west-1 2>$null
            if ($logGroups) {
                $logGroupData = $logGroups | ConvertFrom-Json
                if ($logGroupData.logGroups -and $logGroupData.logGroups.Count -gt 0) {
                    $logGroupExists = $true
                    Write-Host "Log group found! Starting to monitor logs..." -ForegroundColor Green
                }
            }
        } catch {
            # Log group doesn't exist yet, continue waiting
        }
        
        if (-not $logGroupExists) {
            Write-Host "Waiting for log group... ($waitTime/$maxWaitTime seconds)" -ForegroundColor Yellow
            Start-Sleep -Seconds 10
            $waitTime += 10
        }
    }
    
    if (-not $logGroupExists) {
        Write-Host "Warning: Log group not created within 5 minutes. The instance may have failed to start." -ForegroundColor Red
        Write-Host "Trying to monitor logs anyway..." -ForegroundColor Yellow
    }
    
    # Use aws logs tail to follow the logs
    Write-Host "Starting log monitoring..." -ForegroundColor Green
    aws logs tail /aws/parliament/import --follow --region eu-west-1
    
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
} finally {
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host "Log monitoring ended" -ForegroundColor Cyan
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    if ($instanceId) {
        Write-Host "Instance ID: $instanceId" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To check instance status:" -ForegroundColor Cyan
        Write-Host "aws ec2 describe-instances --instance-ids $instanceId"
        Write-Host ""
        Write-Host "To manually check logs:" -ForegroundColor Cyan
        Write-Host "aws logs tail /aws/parliament/import --follow"
        Write-Host ""
        Write-Host "To terminate instance (if still running):" -ForegroundColor Cyan
        Write-Host "aws ec2 terminate-instances --instance-ids $instanceId"
    }
    
    Write-Host "============================================================================" -ForegroundColor Cyan
    
    # Clean up response file
    if (Test-Path response.json) {
        Remove-Item response.json
    }
}