# Changelog

## 0.2.0 — 2026-11-14
- Hardened production configuration validation and browser/API security headers.
- Added request correlation IDs and no-store policies for API responses.
- Made database pool initialization independent for each of the five databases.
- Added owner-scoped module activity API for ingestion, model registry and audit records.
- Added an adult-only NEXORA learner workspace with explicit versioned consent, append-only consent history, goals, learning paths and JSON data export.
- Blocked learner goal creation and updates when consent is not active.
- Added an idempotent NEXORA consent migration and Windows migration helper for pre-existing volumes.
- Hardened the API container with a non-root user, read-only filesystem, dropped capabilities, no-new-privileges and healthcheck.
- Added GitHub Actions checks for Python, JavaScript, tests, Bandit, dependency audit, Compose configuration and container build.
- Added Dependabot update policies, `.dockerignore`, and `.editorconfig`.
- Bumped PWA cache version to invalidate the previous static shell.
- Added a detailed Antigravity runbook and an independent Codex review prompt.
- Updated documentation and the next-phase engineering prompt.

## 0.1.0 — 2026-11-13
- Initial MISHKAT unified-platform engineering package.
- Five independent PostgreSQL/PostGIS databases and domain schemas.
- Owner-scoped RLS and composite owner-aware foreign keys.
- Unified Arabic RTL responsive frontend and PWA shell.
- FastAPI gateway, local-only development JWT and production JWKS verification path.
- Source registry, ingestion provenance and model registry tables per domain.
- NASA POWER daily data connector with separate AGRONEX/ENERGIS persistence.
- Scientific governance, security, roadmap and acceptance documentation.


## 2026-11-14 — Antigravity One-Shot Build Pack

- إضافة `MASTER_PROMPT_ANTIGRAVITY_ONE_SHOT_AR.md` بوصفه التوجيه التنفيذي الموحد الذي يجمع نطاق المنتج والمعمارية والأمن والبيانات والذكاء الاصطناعي والاختبارات والتسليم.
- إضافة `START_HERE_ANTIGRAVITY_AR.md` لتوضيح استخدام الحزمة في Workspace واحد.
- الحفاظ على البرومبتات والوثائق السابقة داخل `docs/`، وإضافة نسخة v0.1.0 التاريخية في `docs/archive/` لأغراض الرجوع فقط.
- لا يتغير إصدار التطبيق نفسه عن 0.2.0؛ هذه حزمة توجيه وتجميع للمستودع وليست ادعاءً بإصدار برمجي جديد.
