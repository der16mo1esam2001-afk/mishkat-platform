$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'Docker Desktop غير موجود أو غير مضاف إلى PATH. ثبّت Docker Desktop وشغّله أولاً.' -ForegroundColor Red
    exit 1
}

docker compose version | Out-Null
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'تم إنشاء ملف .env. افتحه واستبدل كلمات المرور والأسرار، ثم شغّل هذا الملف مرة أخرى.' -ForegroundColor Yellow
    exit 0
}

$envText = Get-Content '.env' -Raw
if ($envText -match 'replace-with-' -or $envText -match 'CHANGE-ME') {
    Write-Host 'يحتوي .env على قيم افتراضية. غيّر كلمات المرور والأسرار أولاً.' -ForegroundColor Yellow
    exit 1
}

docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Host 'تعذر تشغيل الخدمات. راجع رسائل Docker أعلاه.' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host 'تم إرسال أمر تشغيل منصة مِشكاة. تحقق من الجاهزية عبر http://localhost:8000/api/v1/health/ready' -ForegroundColor Green
Start-Process 'http://localhost:8000'
