# Generate SSH Deploy Key for Parliament GitHub Repository

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Parliament GitHub Deploy Key Setup" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

# Create temporary directory for key generation
$tempDir = Join-Path $env:TEMP "parliament-ssh-keys"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

$privateKeyPath = Join-Path $tempDir "parliament_deploy_key"
$publicKeyPath = "$privateKeyPath.pub"

Write-Host "Generating SSH key pair..." -ForegroundColor Green

# Generate SSH key pair (no passphrase for automation)
& ssh-keygen -t rsa -b 4096 -f $privateKeyPath -N '""' -C "parliament-spot-instances@fiscaliza.pt"

if (-not (Test-Path $privateKeyPath)) {
    Write-Host "ERROR: Failed to generate SSH key" -ForegroundColor Red
    exit 1
}

Write-Host "SSH key pair generated successfully!" -ForegroundColor Green

# Read the keys
$privateKey = Get-Content $privateKeyPath -Raw
$publicKey = Get-Content $publicKeyPath -Raw

Write-Host "Storing private key in AWS Secrets Manager..." -ForegroundColor Green

# Store private key in Secrets Manager
$secretName = "fiscaliza-prod-github-deploy-key"
$secretValue = @{
    private_key = $privateKey
    public_key = $publicKey
    repository = "https://github.com/rfsbraz/parliament"
    created_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss UTC")
} | ConvertTo-Json

# Try to create the secret
Write-Host "Creating secret in AWS Secrets Manager..." -ForegroundColor Yellow
& aws secretsmanager create-secret --name $secretName --description "SSH deploy key for Parliament GitHub repository" --secret-string $secretValue --region eu-west-1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Secret may already exist, trying to update..." -ForegroundColor Yellow
    & aws secretsmanager update-secret --secret-id $secretName --secret-string $secretValue --region eu-west-1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Secret updated successfully" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Failed to store secret" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Secret created successfully" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Copy the PUBLIC key below and add it as a Deploy Key in GitHub:" -ForegroundColor Yellow
Write-Host ""
Write-Host "GitHub Repository: https://github.com/rfsbraz/parliament" -ForegroundColor White
Write-Host "Go to: Settings > Deploy keys > Add deploy key" -ForegroundColor White
Write-Host ""
Write-Host "PUBLIC KEY (copy this):" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host $publicKey -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Give the deploy key a name like: 'Parliament Spot Instances'" -ForegroundColor Yellow
Write-Host "3. Make sure 'Allow write access' is UNCHECKED (read-only access)" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan

# Clean up temporary files
Remove-Item $tempDir -Recurse -Force
Write-Host "Setup complete! Press any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")