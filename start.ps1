# SpaceFlow — start backend, frontend, and 3D viewer in separate windows.
# Usage: .\start.ps1

$ErrorActionPreference = "SilentlyContinue"
$Root = $PSScriptRoot

function Stop-Port([int]$Port) {
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
}

Write-Host ""
Write-Host "SpaceFlow — starting all services" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Clearing ports 8082, 5173, 3000..."
foreach ($port in 8082, 5173, 3000) { Stop-Port $port }
Start-Sleep -Seconds 1

Write-Host "Starting Backend API (port 8082)..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\backend'; Write-Host 'SpaceFlow Backend — http://localhost:8082/docs' -ForegroundColor Green; python run.py"
)

Start-Sleep -Seconds 2

Write-Host "Starting Frontend (port 5173)..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\frontend'; Write-Host 'SpaceFlow Frontend — http://localhost:5173' -ForegroundColor Green; npm run dev"
)

Write-Host "Starting 3D Viewer (port 3000)..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\tumo_3d_model'; Write-Host 'TUMO 3D Viewer — http://localhost:3000' -ForegroundColor Green; npm start"
)

Write-Host ""
Write-Host "Services launched in new windows:" -ForegroundColor Green
Write-Host "  Backend API   http://localhost:8082/docs"
Write-Host "  Frontend      http://localhost:5173"
Write-Host "  3D Viewer     http://localhost:3000"
Write-Host ""
Write-Host "Wait a few seconds, then open the frontend or 3D viewer in your browser."
Write-Host ""
