$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-Not (Test-Path $python)) {
    Write-Error "Python executable not found at $python. Activate your venv or run from project root."
    exit 1
}
$port = $env:PORT
if (-not $port) { $port = 8001 }
# Start server in background
$proc = Start-Process -FilePath $python -ArgumentList "run_server.py" -WorkingDirectory $root -PassThru
Write-Host "Started server (PID=$($proc.Id)). Waiting for http://127.0.0.1:$port/ to become available..."
# Wait for server to be up
$maxAttempts = 60
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$port/" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            Write-Host "Server is up. Opening browser to /chat"
            Start-Process "http://127.0.0.1:$port/chat"
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 1
        $attempt++
    }
}
Write-Warning "Server did not become ready within timeout. Check logs. PID=$($proc.Id)"
exit 1
