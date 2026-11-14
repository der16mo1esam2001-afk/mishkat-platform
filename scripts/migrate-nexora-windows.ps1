$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".env")) {
    throw "ملف .env غير موجود. انسخ .env.example إلى .env وأدخل كلمات مرور قوية أولاً."
}

Write-Host "تطبيق ترحيل سجل الموافقات على قاعدة NEXORA الحالية..." -ForegroundColor Cyan
docker compose exec -T nexora-db psql -U postgres -d nexora -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/03-learner-consents.sql
if ($LASTEXITCODE -ne 0) { throw "فشل ترحيل قاعدة NEXORA." }
Write-Host "اكتمل الترحيل. تحقق من الجداول وسياسات RLS قبل إدخال بيانات حقيقية." -ForegroundColor Green
