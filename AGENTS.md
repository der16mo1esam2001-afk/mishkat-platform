# MISHKAT Engineering Rules

These rules apply to every coding agent and contributor working in this repository.

## Product truth
- MISHKAT is one user experience with five isolated data domains: VITALIS, AQUANEX, AGRONEX, ENERGIS, and NEXORA.
- Keep five independent PostgreSQL databases. Do not consolidate domain records into a shared database.
- The current product is an engineering pilot. Do not claim production readiness, scientific validation, certification, or live integrations unless the evidence exists in this repository and tests.
- Never display synthetic numbers as real measurements. Label fixtures and demo data explicitly.

## Data and scientific integrity
- Every imported value must preserve source, retrieval time, observation time, unit, geography, license/terms snapshot, raw payload reference, and transformation version where applicable.
- Distinguish observed, self-reported, official aggregate, remotely sensed/gridded, estimated, and forecast values.
- Never turn missing values into zero.
- Do not infer patient-level, farm-level, utility-level, or learner-level facts from country-level aggregates.
- Use current official source documentation. Check access, licensing, rate limits, schema and update cadence before implementing a connector.

## Security and privacy
- The browser is untrusted. Never ship database passwords, service-role keys, model-provider secrets, signing secrets, or privileged credentials to the frontend.
- Derive owner identity only from a verified authentication token. Never accept owner_id from request bodies as an authorization source.
- Keep owner-scoped RLS enabled and forced. Keep composite owner-aware foreign keys for relationships between tenant-owned records.
- Never use BYPASSRLS for application roles.
- Development authentication must never be reachable in production. Production startup must fail closed when identity, secrets, CORS or required configuration is unsafe.
- Do not use real patient or student data during local tests. NEXORA's current pilot is adult-only; do not register minors until safeguarding, guardian consent, and legal review are implemented.
- No autonomous diagnosis, treatment, water-network actuation, grid control, or pesticide instruction.

## Engineering workflow
- Inspect the repository and existing behavior before editing. Create a branch/checkpoint first.
- Make small, reviewable changes. Prefer migrations and backward-compatible APIs over destructive rewrites.
- Do not overwrite user data, delete volumes, reset databases, publish, or deploy without explicit user approval.
- Use parameterized SQL and explicit allowlists. Validate all external API payloads and all user inputs.
- Add tests for every bug fix and new workflow. Run the full available suite after each milestone.
- Record exact commands, pass/fail counts, and unavailable checks. Never invent test results.
- Keep the README, changelog, build-status report, API docs, and roadmap in sync.
- If a task requires credentials, real institutional data, licenses, an external partner, or an expert approval, build the integration boundary and document the blocker; do not fabricate access.

## Release gate
A release candidate must have no unresolved critical/high findings from the defined security review, all critical user journeys passing in CI, tested migrations, verified RLS isolation, backup/restore evidence, accessibility checks, and a documented rollback plan. A green unit-test run alone is not a production release.
