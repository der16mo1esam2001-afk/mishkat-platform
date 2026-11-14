$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
docker compose down
Write-Host 'تم إيقاف خدمات مِشكاة مع الإبقاء على أحجام قواعد البيانات.' -ForegroundColor Green
