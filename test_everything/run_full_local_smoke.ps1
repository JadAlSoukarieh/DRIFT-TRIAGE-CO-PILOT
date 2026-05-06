$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PlatformPython = "C:\Users\Jad\AppData\Local\Temp\uv-python\cpython-3.12.13-windows-x86_64-none\python.exe"
$TestPostgresName = "drift-test-postgres"
$TestPostgresPort = "15432"

function Stop-PortProcess {
    param([int]$Port)

    $lines = netstat -ano | findstr ":$Port " | findstr LISTENING
    foreach ($line in $lines) {
        $parts = ($line -split "\s+") | Where-Object { $_ }
        if ($parts.Count -ge 5) {
            Stop-Process -Id ([int]$parts[-1]) -Force -ErrorAction SilentlyContinue
        }
    }
}

function Ensure-TestPostgres {
    $existing = docker ps -a --filter "name=$TestPostgresName" --format "{{.Names}}"
    if ($existing -contains $TestPostgresName) {
        docker start $TestPostgresName | Out-Null
    } else {
        docker run --name $TestPostgresName `
            -e POSTGRES_USER=user `
            -e POSTGRES_PASSWORD=pass `
            -e POSTGRES_DB=drift `
            -p "${TestPostgresPort}:5432" `
            -d postgres:16 | Out-Null
        Start-Sleep -Seconds 5
    }

    Get-Content (Join-Path $Root "postgres\init.sql") |
        docker exec -i $TestPostgresName psql -U user -d drift | Out-Null
}

Set-Location $Root

docker compose up -d redis | Out-Null
Ensure-TestPostgres

Stop-PortProcess -Port 8000
Stop-PortProcess -Port 8001
Stop-PortProcess -Port 8501
Start-Sleep -Seconds 1

$env:POSTGRES_DSN = "postgresql://user:pass@127.0.0.1:$TestPostgresPort/drift"
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:PLATFORM_BASE_URL = "http://127.0.0.1:8000"
$env:LLM_PROVIDER = "mock"
$env:LLM_MODEL = "mock"
$agent = Start-Process -FilePath python `
    -ArgumentList @("-m", "uvicorn", "agent.app.main:app", "--host", "127.0.0.1", "--port", "8001") `
    -WorkingDirectory $Root `
    -PassThru `
    -WindowStyle Hidden

$env:AGENT_BASE_URL = "http://127.0.0.1:8001"
$env:PYTHONPATH = (Resolve-Path (Join-Path $Root "platform\.venv\Lib\site-packages")).Path
$platform = Start-Process -FilePath $PlatformPython `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory (Join-Path $Root "platform") `
    -PassThru `
    -WindowStyle Hidden

$env:PLATFORM_BASE_URL = "http://127.0.0.1:8000"
$dashboard = Start-Process -FilePath python `
    -ArgumentList @("-m", "streamlit", "run", "dashboard/app.py", "--server.address", "127.0.0.1", "--server.port", "8501", "--server.headless", "true", "--browser.gatherUsageStats", "false") `
    -WorkingDirectory $Root `
    -PassThru `
    -WindowStyle Hidden

Start-Sleep -Seconds 5

Write-Output "agent PID=$($agent.Id) http://127.0.0.1:8001"
Write-Output "platform PID=$($platform.Id) http://127.0.0.1:8000"
Write-Output "dashboard PID=$($dashboard.Id) http://127.0.0.1:8501"
Write-Output "agent health: $((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8001/health).Content)"
Write-Output "platform health: $((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health).Content)"
Write-Output "dashboard status: $((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8501).StatusCode)"
Write-Output "drift report: $((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/drift/report).Content)"
Write-Output "hil pending: $((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8001/hil/pending).Content)"
Write-Output "Open http://127.0.0.1:8501 to test the dashboard."
