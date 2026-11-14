# MASTER PROMPT — MISHKAT v0.2.x إلى Release Candidate مؤسسي

> **طريقة الاستخدام:** افتح مجلد `mishkat-platform` بالكامل في Antigravity، واجعل وضع التخطيط Plan أولاً، ثم الصق هذا البرومبت. بعد مراجعة الخطة، انتقل إلى Agent ونفّذ مرحلة واحدة في كل مرة. لا تضع ملف `.env` أو كلمات مرور أو مفاتيح API داخل المحادثة أو مستودع Git.

---

## 0. المهمة والنتيجة المطلوبة

أنت فريق هندسي متعدد التخصصات يعمل على مستودع MISHKAT الحالي، لا على مشروع جديد متخيل. مهمتك نقل المستودع من الإصدار الهندسي الأولي إلى **منصة تجريبية مؤسسية قابلة للتحقق والتوسع، ثم إعداد Release Candidate** بعد اجتياز بوابات الاختبار والأمن والبيانات والحوكمة.

اسم المنصة: **مِشكاة | MISHKAT**
الشعار: **من جذور المعرفة إلى آفاق المستقبل**
المنتج: منصة موحدة في الهوية والتجربة، مكوّنة من خمسة أنظمة قطاعية مستقلة:
1. VITALIS AI — الصحة والوقاية.
2. AQUANEX — استخبارات المياه.
3. AGRONEX — الزراعة والأمن الغذائي.
4. ENERGIS — استخبارات الطاقة.
5. NEXORA — التعليم والذكاء المعرفي الشخصي.

لا تعد المستخدم بأن المنصة ستصبح رقم 1 عالمياً أو خالية من الأخطاء. لا توجد طريقة هندسية لإثبات نسبة خطأ صفر. الهدف هو تقليل المخاطر المنهجية، وإظهار كل قيد معروف، وعدم إطلاق إصدار إنتاجي قبل اجتياز اختبارات مستقلة وبوابات اعتماد القطاع.

## 1. الدور المطلوب منك

تصرف كفريق متكامل يضم:
- Principal Architect / Technical Product Lead.
- Backend Engineer (Python, FastAPI, PostgreSQL).
- Frontend Engineer (accessible responsive web, Arabic RTL and English LTR).
- Data Engineer / Geospatial Engineer.
- AI/ML Engineer and Evaluation Specialist.
- Application Security Engineer.
- QA Automation / Performance Engineer.
- DevOps / SRE.
- Domain reviewers for health, water, agriculture, energy, and education.

استخدم الوكلاء المتخصصين بالتوازي فقط للمهام المستقلة، مع مراجعة بشرية موحدة للقرارات المعمارية. لا تسمح لوكيل بتعديل مخطط قاعدة بيانات قطاع آخر. أنشئ فروع Git أو worktrees منفصلة عند العمل المتوازي، ثم ادمج التغييرات بعد مراجعة diff والاختبارات.

## 2. ابدأ بفحص المستودع لا بإعادة كتابته

قبل أي تعديل:
1. اقرأ `AGENTS.md`, `README_AR.md`, `docs/BUILD_STATUS_AR.md`, `docs/ARCHITECTURE_AR.md`, `docs/PRODUCT_BLUEPRINT_AR.md`, `docs/SCIENCE_AND_DATA_GOVERNANCE_AR.md`, `docs/SECURITY_THREAT_MODEL_AR.md`, `docs/ACCEPTANCE_CRITERIA_AR.md`, و`docs/ROADMAP_AR.md`.
2. افحص كل ملفات التطبيق والمخططات والترحيلات وسكربتات التشغيل والاختبارات.
3. أنشئ تقرير حالة يفرق بين: implemented, tested, manually verified, externally blocked, planned.
4. حدد التناقضات بين README والكود والمخططات ثم صححها.
5. أنشئ خطة تغيير صغيرة مع مخاطر وترحيلات وخطة rollback.

لا تنفذ `docker compose down -v` أو reset أو drop database أو حذف ملفات أو نشر أو تعديل بيئة إنتاج. لا تستبدل الواجهة أو إطار العمل بالكامل لمجرد تفضيل تقني. قدّم ADR قبل أي انتقال كبير، واثبت أن كلفة الترحيل أقل من فائدته.

## 3. المعمارية غير القابلة للتفاوض

### 3.1 تجربة واحدة، بيانات منفصلة
- واجهة MISHKAT موحدة، مع مراكز عمل لكل قطاع.
- خمس قواعد PostgreSQL منفصلة فعلياً: `vitalis`, `aquanex`, `agronex`, `energis`, `nexora`.
- لا تنشئ قاعدة بيانات قطاعية مشتركة ولا schema واحداً يجمع سجلات المرضى والطلاب والمزارع والمياه والطاقة.
- يمكن مشاركة مكتبات الواجهة، وعقود API العامة، وسجل مصادر البيانات غير الحساسة، ومعايير المراقبة، لكن لا تخلط بيانات المجالات.
- أي تبادل بين القطاعات يتم عبر API موثق، بغرض محدد، وموافقة وصلاحية وسجل تدقيق.

### 3.2 التقنيات الحالية
- Backend: Python + FastAPI.
- Databases: PostgreSQL منفصلة لكل قطاع، وPostGIS للبيانات المكانية حيث يلزم.
- Frontend الحالي: HTML/CSS/JavaScript وPWA shell.
- Auth الحالي: رمز تطوير محلي فقط، ومسار JWKS يحتاج إعداد موفر هوية حقيقي.
- Docker Compose للتطوير المحلي.

حافظ على هذا الأساس خلال مرحلة تثبيت v0.2.x. قيّم الانتقال إلى Next.js + TypeScript أو تطبيق Flutter/React Native في ADR مستقل، مع خطة هجرة قابلة للتراجع. لا تجرِ rewrite شاملاً في خطوة واحدة.

### 3.3 حدود الثقة
- المتصفح غير موثوق.
- API هو الوسيط الوحيد لقواعد البيانات.
- قواعد البيانات لا تُنشر على منافذ عامة.
- أسرار الموردين ومفاتيح قواعد البيانات لا تظهر في الواجهة أو ملفات Git.
- التطبيق لا يستخدم قاعدة البيانات بامتيازات superuser أو BYPASSRLS.

## 4. المزايا المشتركة التي يجب بناؤها

### 4.1 الهوية والمؤسسات
- موفر هوية إنتاجي OIDC/Supabase Auth مع PKCE أو تدفق جلسات آمن.
- أدوار وصلاحيات واضحة: platform admin, organization admin, domain manager, analyst, practitioner, learner, read-only auditor.
- دعم MFA للحسابات الحساسة، وإدارة الجلسات، وتدوير المفاتيح.
- فصل المؤسسة عن المستخدم في تصميم متعدد المؤسسات؛ لا تضف tenant_id إلى المخططات عشوائياً قبل ADR وتصميم عزل مؤسسي صحيح.
- اختبار الوصول بين مستخدمين ومؤسسات منفصلة لكل جدول وكل API.

### 4.2 مركز الأدلة والمصادر
أنشئ سجل بيانات مركزي للبيانات الوصفية، لا نسخة موحدة من السجلات القطاعية. لكل مصدر:
- معرف ثابت، الناشر، الاسم الرسمي، عنوان المصدر.
- الترخيص وشروط النسبة وإعادة الاستخدام.
- طريقة الوصول: public API, API key, bulk download, institutional agreement, research approval.
- schema version، تاريخ آخر تحقق من الموصل، cadence، التغطية الجغرافية، وحدات القياس.
- وقت الاسترجاع ووقت الرصد الأصلي وtimezone.
- نوع القيمة: measured, self_reported, official_aggregate, gridded_remote_sensing, derived, forecast, synthetic_test_fixture.
- quality checks، missingness، transformations، attribution.
- حالة الموصل: catalogued, credential_missing, partner_required, connected, degraded, disabled.

لا تعتبر ظهور مصدر في catalog دليلاً على اتصال الموصل أو امتلاك ترخيص استخدام كل مجموعة بيانات.

### 4.3 جودة البيانات وخطوط الاستيراد
- Adapter منفصل لكل مصدر.
- schema validation قبل التخزين.
- فحص الوحدات والمدى والوقت والإحداثيات والقيم المفقودة.
- raw payload reference مع hashing أو تخزين خام مقيد، ثم normalized tables.
- idempotency key لمنع التكرار.
- retries بتأخير تصاعدي، timeouts، rate limits، dead-letter/error state.
- ingestion_runs تفصيلية وسجل audit.
- منع تحويل missing إلى zero.
- منع إدخال مصدر خارجي إلى جدول قطاع غير مالك له.
- ربط كل رقم في dashboard بمصدر وفترة ووحدة وحالة جودة.

### 4.4 بوابة الذكاء الاصطناعي
أنشئ واجهة AI Gateway قابلة لتعدد الموردين، لكن اترك الاستدلال مغلقاً افتراضياً حتى تكوين المزود والعقود والأسرار والتقييم.
- model registry: provider, model, version, purpose, status, context policy, data-processing terms.
- prompt/version registry، trace IDs، cost/latency metrics، safety filters.
- Retrieval-Augmented Generation بمصادر مصرح بها، مع citation ID وpage/section/URL وretrieval timestamp.
- إذا لم يوجد دليل كافٍ، ارفض الإجابة أو قل إن المصدر غير متاح.
- افصل الحقائق المسترجعة عن التفسير والاستنتاج والتوقع.
- لا تستخدم محادثات العملاء لتدريب النماذج دون موافقة صريحة واتفاقية مناسبة.
- أي Agent يملك صلاحيات محدودة ومجموعة أدوات Allowlist. عمليات الكتابة الخارجية تتطلب موافقة بشرية. لا توجد أوامر تشغيل مادية للأنظمة الحيوية.
- أضف evaluation datasets مرخصة، gold sets، adversarial prompts، regression tests، drift detection، rollback to prior model.

### 4.5 تجربة المستخدم
- واجهة عربية RTL وإنجليزية LTR حقيقية، وليست ترجمة آلية غير مراجعة.
- تصميم متجاوب، keyboard-only navigation، screen-reader labels، contrast، reduced motion.
- استهدف WCAG 2.2 AA واختبره بالأدوات وبمراجعة يدوية.
- شاشات loading/empty/error/offline واضحة.
- لا تستخدم رسوم أو badges لإخفاء غياب البيانات.
- أي chart يوضح المصدر والفترة والوحدة ونوع البيانات.
- بحث موحد في الصفحات والموارد المصرح بها، وليس بحثاً يكشف بيانات مجال آخر.
- دعم PWA حالياً؛ لا تدّعِ وجود تطبيق متجر أصلي قبل إنشاء تطبيق فعلي واختباره.

## 5. نطاق كل نظام قطاعي

### 5.1 VITALIS AI — الصحة
- ملفات مرضى مستعارة pseudonymous، وموافقات، وزيارات، وملاحظات سريرية منظمة، وملاحظات وعلامات حيوية، وخطط رعاية يراجعها مختص.
- سجل زمني للمريض مع مصدر كل معلومة وتاريخها ووحدتها.
- واجهات تكامل FHIR ومطابقة profiles يحددها الشريك. استخدم FHIR R5 كإصدار منشور حالياً ما لم يتطلب شريك محلي إصداراً آخر؛ تعامل مع R6 باعتباره مسار تطوير/ballot حتى نشر نسخة معيارية نهائية.
- مفردات مثل ICD أو SNOMED CT لا تستخدم إلا بعد مراجعة التراخيص وشروط التوزيع.
- تقارير تشغيلية مجمعة مع منع إعادة التعرف على المرضى.
- لا تشخيص، لا وصف علاج، لا فرز سريري مستقل، ولا استخدام علاجي إلا بعد شريك سريري، لجنة أخلاقيات، تحقق سريري وتنظيمي، ومراجعة قانونية محلية.

### 5.2 AQUANEX — المياه
- GIS للأصول: شبكات، أنابيب، مضخات، خزانات، محطات، مناطق خدمة.
- قراءات الضغط والتدفق والمناسيب وجودة المياه مع وحدات ومعايرة وسجل الجهاز.
- عينات مختبر، نتائج، حدود مرجعية من الجهة المختصة، alerts وwork orders.
- مؤشر تسرب احتمالي لا يصبح حدثاً مؤكداً إلا بعد تحقق ميداني.
- مؤشرات مخاطر WRI/FAO تظل مخاطر استراتيجية ولا تُعرض كقياس مباشر لشبكة أو عينة.
- لا أوامر تحكم بالصمامات أو المضخات من هذا المنتج؛ أي تكامل OT لاحق يحتاج شبكة منفصلة، مراجعة ICS security، وinterlocks بشرية.

### 5.3 AGRONEX — الزراعة والغذاء
- مؤسسات/مزارع/قطع جغرافية، دورات محاصيل، تقويم زراعي، أصناف، عينات تربة، الطقس، صور الأقمار الصناعية، أحداث الري، المدخلات، الحصاد.
- تكامل FAOSTAT وFAO WaPOR وNASA POWER بعد التحقق من الوصول والترخيص والحقول والتغطية.
- تحليلات crop health، مع وسم `suspected` لا `confirmed` عند تحليل الصور.
- تقدير الإنتاج مع فترات ثقة وتقييم مستقل حسب محصول وموسم ومنطقة.
- لا توصية مبيدات أو جرعات كيميائية دون محتوى محلي مرخص ومراجعة خبير زراعي.
- لا تستخدم بيانات دولة أو قمر صناعي على أنها قراءة حقل أو مزرعة مباشرة.

### 5.4 ENERGIS — الطاقة
- منشآت ومواقع وأصول ومعدات وعدادات وفترات قراءة ووحدات.
- بيانات generation وconsumption منفصلة عن solar resource/weather.
- تكامل Ember للإحصاءات العامة وNASA POWER للإشعاع/الطقس، وبيانات NREA المنشورة. لا تصفها كقراءة SCADA أو عداد لحظية.
- load forecasting مع baseline بسيط ومقاييس خطأ وفترات عدم يقين.
- anomaly detection ومهام صيانة تتطلب مراجعة مشغل.
- لا تحكم في الشبكات أو المحولات أو البطاريات من نموذج تنبؤي.

### 5.5 NEXORA — التعليم والمعرفة
- learner profiles بمبدأ data minimization، أهداف، مهارات، مصادر تعليمية مرخصة، learning paths، units، assessments، attempts، mastery records.
- المحتوى الرقمي يسجل الناشر والترخيص والرابط والإصدار وحقوق التضمين.
- مسارات تعليمية تتضمن تشخيصاً قبلياً، تعلم وممارسة واسترجاعاً متباعداً، تقييماً بعدياً، وقياس احتفاظ لاحق.
- لا تعتبر مشاهدة المحتوى إتقاناً.
- لا تخلط إحصاءات UNESCO أو CAPMAS مع سجلات طالب فردي.
- حماية القاصرين تتطلب age assurance متناسباً، موافقات ولي الأمر والمؤسسة، safeguarding، مراجعة قانونية، وضوابط خاصة؛ لا تفعّل حسابات القاصرين قبل اكتمال ذلك.
- AI tutor / research copilot يستشهد بالمصادر المرخصة ولا يولد اقتباسات أو صفحات وهمية.

## 6. الواجهات واللوحات المطلوبة

1. Portfolio Overview: صحة الخدمات الخمس، مصادر البيانات، حالات الاستيراد، نماذج معتمدة/غير معتمدة، تنبيهات موثقة.
2. Domain Workspaces: لوحة منفصلة لكل مجال مع workflows حقيقية.
3. Evidence Center: سجل المصدر، الترخيص، الجودة، lineage، تحديث البيانات.
4. Model & AI Governance: النماذج، الإصدارات، التقييمات، حدود الاستخدام، موافقات النشر.
5. Audit Center: سجلات تدقيق قابلة للتصفية والتصدير وفق الصلاحيات.
6. Organization & Access: أعضاء، أدوار، صلاحيات، جلسات، موافقات.
7. Data Operations: موصلات، jobs، imports، retry، failures، freshness.
8. Impact Center: KPI مع baseline ومنهجية وsource وconfidence؛ لا تعرض أرقاماً إذا لم تتوفر بيانات.
9. Admin / Settings: feature flags، secret references (not secrets), locale، retention، system health.
10. Help & Documentation: أدلة المستخدم والمسؤول والتشغيل.

## 7. الأمن والامتثال

استخدم OWASP ASVS 5.0.0 بوصفه قائمة تحقق تقنية مستقرة، وNIST AI RMF مع ملفات الذكاء الاصطناعي التوليدي/البنية التحتية الحيوية ذات الصلة. لا تدّعِ امتثالاً قانونياً أو اعتماداً من مجرد اتباع checklist.
- JWT/JWKS validation: issuer, audience, expiration, signing algorithm allowlist, key rotation.
- MFA/SSO عند ملاءمتها.
- RLS ENABLE + FORCE على كل جدول يخص مستخدم/مؤسسة.
- composite foreign keys owner-aware في العلاقات التابعة.
- negative tests A/B across every table and endpoint.
- secrets manager، rotation، no secrets in browser or Git history.
- HTTPS/TLS، HSTS، CSP، CSRF/XSS/SQLi protections، secure cookies.
- API rate limits distributed where production requires multiple API replicas.
- audit log immutable-by-app-role; no sensitive content in logs.
- encryption at rest/in transit، backup encryption، tested restores.
- data retention, export, deletion, access requests, consent versioning.
- dependency/SBOM scanning, SAST, DAST, container scanning, secret scanning.
- incident response, threat model, asset inventory and disaster recovery.
- legal analysis per country, especially Egyptian Personal Data Protection Law and any health/minor/critical-infrastructure rules. Get qualified local counsel; do not present AI-generated text as legal advice.

## 8. التشغيل والاعتمادية

- Separate environments: local, CI, staging, production.
- Containers run non-root, drop unnecessary capabilities, no-new-privileges, read-only filesystem where possible.
- Health endpoints: liveness vs readiness; readiness should report each database independently.
- Structured logs with request/correlation IDs and redaction.
- Metrics: latency, error rate, queue age, DB pool saturation, ingestion freshness, external API failures, model latency and cost.
- Tracing across API → connector → database.
- Backups + PITR strategy appropriate to managed DB provider; perform restore drills.
- CI on every pull request: format, lint, type check, migrations test, unit, integration, security, E2E, accessibility smoke, container build.
- release tags, changelog, deployment manifest, migration and rollback plan.
- SLOs defined by user-facing critical journeys; do not invent availability history.

## 9. Testing and evidence gates

Write tests for:
- Every critical business rule.
- API request/response schemas.
- SQL migrations against real PostgreSQL/PostGIS containers in CI.
- RLS owner isolation and cross-domain isolation.
- External API contract tests using sanitized recorded fixtures clearly marked as fixtures; add live smoke test only in a network-enabled CI job with rate controls.
- PWA offline shell and confirmation that API/sensitive responses are never cached.
- UI end-to-end flows on Chromium and a second browser engine before release.
- Arabic RTL, keyboard, screen readers, zoom and mobile breakpoints.
- AI groundedness, citation accuracy, refusal behavior, harmful prompt tests, subgroup performance, calibration, drift and rollback.

Acceptance targets (adjust with evidence and document exceptions):
- All critical user journeys pass.
- No unresolved critical/high security finding before pilot release.
- Every endpoint has positive and negative authorization tests.
- Every external data value shown to users exposes provenance and unit/time context.
- No untested migration reaches production.
- No model with status other than validated/approved can serve a high-impact decision.
- Use meaningful coverage targets (e.g. 80%+ for core domain logic) but prioritize critical-path tests over vanity coverage. Do not claim zero defects.

## 10. تنفيذ مرحلي إلزامي

### Milestone A — Repository hardening
- Review current changes from v0.2.0.
- Run all current tests.
- Fix security/configuration defects.
- Add CI, dependency/SBOM checks and migration test harness.
- Produce ADRs for auth, tenancy, frontend strategy and hosting.

### Milestone B — Real identity and tenancy
- Implement production auth flow and session lifecycle.
- Define organization membership and permissions.
- Add RLS tests for all five databases.
- Remove dev-auth path from all production builds.

### Milestone C — Data operations
- Build connector framework, data catalog, ingestion jobs, provenance, freshness, quality tests and per-source license gates.
- Implement one verified source connector per sector; never declare a source connected until a live test and stored provenance prove it.

### Milestone D — Working domain MVPs
- Complete one thin vertical workflow in each sector end-to-end, with real forms, server validation, database writes, list/detail/edit, audit trail, and tests.
- Prefer one pilot cohort/site/farm/facility/resource set at first.
- Do not build advanced predictions before sufficient data is obtained.

### Milestone E — AI gateway and retrieval
- Implement provider abstraction, server-only secrets, consent and data minimization, RAG with citations, model registry and evaluation pipeline.
- Start with low-risk educational/research assistant or descriptive analytics. Keep clinical and critical-infrastructure AI disabled until their independent approvals.

### Milestone F — Domain intelligence
- Build models only where enough lawful, representative data exists.
- Establish baseline metrics, temporal/geographic splits, external validation, confidence intervals, subgroup testing and model cards.
- No model may silently act on physical systems.

### Milestone G — UX, mobile and accessibility
- Complete responsive web experience, language switch, accessible forms, keyboard and screen reader checks.
- Define native mobile needs; deliver PWA first unless offline/device integration requirements justify Flutter/React Native.

### Milestone H — Production readiness
- Staging and production infrastructure, managed secrets, backups, restore tests, monitoring, rate limits, vulnerability scans, external penetration test, legal/privacy review, runbooks and rollback.
- Deploy only after explicit human approval and after required credentials/agreements are available.

## 11. Rules for agent collaboration

- One lead agent owns architecture and integration.
- Separate subagents may review: frontend/accessibility, backend/API, PostgreSQL/RLS, sector data connectors, QA/security.
- Each subagent gets a bounded task and file ownership. Do not let multiple agents edit the same migration or file concurrently.
- The integration agent must review every diff, run tests, reconcile API contracts, and update docs.
- Require approvals for: destructive DB commands, real-data uploads, contacting external services that might incur cost, deployment, domain/DNS changes, and changes to production secrets.

## 12. Required deliverables at every milestone

- Implementation plan and completed checklist.
- Architecture/ADR updates.
- Database migration(s) with rollback guidance.
- API specification / OpenAPI changes.
- UI screenshots and E2E evidence.
- Test report with exact commands and test counts.
- Security findings (severity, evidence, disposition).
- Data source register and license/access status.
- Known limitations and external dependencies.
- Updated `BUILD_STATUS_AR.md`, `ROADMAP_AR.md`, `CHANGELOG.md`, `README_AR.md`.

## 13. Final instruction

ابدأ الآن بمراجعة المستودع وتحديد milestone الأقرب، ولا تقفز مباشرة إلى كتابة مئات الملفات. قدّم خطة مرتبة مع تقدير المخاطر والاعتماديات، ثم نفّذ milestone واحداً كاملاً. بعد كل milestone شغّل الاختبارات وأصلح الفشل قبل متابعة التالي. لا تتوقف بعد كتابة الخطة فقط، لكن لا تعلن النجاح قبل إثباته.

When blocked by missing API credentials, licensed data, institutional partners, domain approvals, or professional review, deliver the integration boundary, setup documentation, and explicit blocker. Never fabricate credentials, source data, tests, certifications, research citations, or deployment status.

Your output must be a reliable, auditable product—not a speculative demo.

## 14. توسعة المنتج: خصائص عالية القيمة يجب تقييمها وترتيبها

لا تنفذ كل الخصائص دفعة واحدة. حوّلها إلى backlog مبرر، ولكل عنصر (problem, user, business value, dependencies, risk, acceptance test, owner).

### 14.1 منصة مشتركة
- Unified identity مع OIDC/Supabase Auth، MFA، SSO للمؤسسات، إدارة الجلسات، أجهزة موثوقة، واسترداد حساب آمن.
- Organization workspaces، عضويات ودعوات، RBAC + ABAC، صلاحيات دقيقة على مستوى المؤسسة والموقع/المزرعة/المنشأة/المريض/المتعلم.
- Tenant administration، audit explorer، export/deletion requests، consent center، policy versioning.
- Global search آمن يطبق صلاحيات كل قطاع قبل إظهار أي نتيجة؛ لا توجد فهارس مشتركة تكشف بيانات قطاع آخر.
- Notification center مع قنوات Email/SMS/Web push عند تفعيل مزود معتمد، preferences، quiet hours، retries، delivery logs، وقابلية إيقافها.
- Workflow engine لمهام الموافقة والمراجعة والإحالة والعمل والصيانة، مع SLA وescalation وسجل التغييرات.
- Document vault لملفات المؤسسة: antivirus scanning، MIME sniffing، size limits، private buckets، signed URLs قصيرة العمر، retention rules.
- Developer portal للـ API keys ذات النطاقات المحددة، webhooks بتوقيع HMAC وreplay protection، quotas، versioning وSDKs.
- Evidence Center: المصادر، التراخيص، lineage، جودة البيانات، تاريخ الاسترجاع، التحويلات، الوحدات والحدود.
- Impact & Cost Center: KPIs موثقة وخط أساس، ومراقبة تكلفة السحابة والبيانات وAI لكل مؤسسة/قطاع.
- Feature flags، release channels، tenant-level configuration، disaster recovery runbooks.

### 14.2 الذكاء الاصطناعي والوكلاء
- Provider abstraction لتعدد مزودي النماذج من دون ربط النظام بمورد واحد.
- RAG بمصادر مصرح بها، citations قابلة للفتح، إشارة إلى غياب الدليل، retrieval time، version and license.
- Prompt registry/versioning، safety policies، evaluations، red-team datasets، jailbreak tests، hallucination checks، model cards.
- Human-in-the-loop approvals لكل إجراء خارجي أو قرار عالي التأثير.
- Tool allowlists، scoped credentials، read-only default، sandboxing، action preview، approval token، idempotency، rollback/compensation.
- Agent observability: trace, tool calls, latency, failures, costs, user feedback، مع حجب الأسرار والمحتوى الحساس من السجلات.
- Context minimization، PII redaction، data residency controls، provider retention review، opt-in منفصل لتدريب أو حفظ المحادثات.
- لا تسمح لوكيل عام بعبور قواعد البيانات الخمس. كل domain agent يتصل بقاعدة مجاله فقط، والعبور عبر API وسياسة موثقة وموافقة محددة.

### 14.3 VITALIS — إضافات مقترحة بعد شريك سريري
- FHIR R5 interoperability مع implementation guide يتفق عليه الشريك؛ لا تستخدم نماذج R6 غير النهائية كمعيار إنتاج.
- Medication/allergy/problem lists فقط ضمن نطاق سريري يوافق عليه الشريك، مع terminology licensing.
- Appointment and referral workflows، care-plan review، clinical document provenance، patient consent, access logs.
- Clinical decision support في وضع إرشادي فقط، with evidence citations، validation cohort، subgroup testing، silent-mode pilot، وموافقة سريرية/تنظيمية.
- Patient-facing accessibility، Arabic/English language، لكن لا تشخيص ولا وصف دواء تلقائي.

### 14.4 AQUANEX — إضافات مقترحة بعد شريك مرفق مياه
- GIS asset management، field inspection mobile workflows، calibration and sensor maintenance.
- Lab sample chain-of-custody، quality thresholds from approved authority، exception workflow.
- Leak triage with confidence bands and confirmed/unconfirmed states.
- Work order planning، repair outcomes، loss accounting، water balance and district metered areas.
- Read-only integration to SCADA/OT through network segmentation and ICS security review; no write controls.

### 14.5 AGRONEX — إضافات مقترحة بعد شريك زراعي
- Farm/plot registry، crop seasons، agronomic calendar and variety registry.
- Satellite index time series، field observation app، soil-test ingestion and sensor calibration.
- Irrigation planner with crop stage, soil, local weather and uncertainty.
- Plant-health image screening clearly labelled suspected, expert review and feedback.
- Yield prediction with season-region split, forecast intervals, harvest verification and farmer economics.
- Traceability and post-harvest storage/supply chain as a later phase.

### 14.6 ENERGIS — إضافات مقترحة بعد بيانات عدادات ومنشآت
- Energy asset registry, meter hierarchy, tariff catalog, interval readings and data quality.
- Consumption baselines, weather-normalized comparisons, demand forecasts and alerts.
- Solar/wind asset performance, inverter health, battery SoC/SoH only with validated telemetry.
- Maintenance ticket workflow and verified incident outcomes.
- Energy audit reports and cost/emissions calculations with declared factors and factor versions.
- Read-only telemetry integrations initially; no operational control of grid or equipment.

### 14.7 NEXORA — إضافات مقترحة بعد ترخيص المحتوى واختبار التعلم
- Diagnostic pre-test, personal learning paths, spaced retrieval, practice schedules, mastery tests and delayed retention.
- Evidence-grounded AI tutor, research assistant, document summarization with page citations, knowledge graph and source licensing.
- Learning object repository with publisher/author/edition/license/rights, DRM or access rules where needed.
- Teacher/institution workspace, class cohorts, accessibility profiles, intervention workflow and privacy safeguards.
- Multimodal learning: speech-to-text, text-to-speech, captions, transcripts, image understanding; each capability must be tested for Arabic quality and accessibility.
- Parent/guardian and minors' safeguarding only after age assurance, consent, abuse reporting and legal review.
- Academic integrity and assessment policy; do not market generated tests as official exam replicas unless formally approved.

### 14.8 خارطة الأولويات

**P0 — Pilot-safe foundation:** real production identity, owner/tenant isolation, CI, DB migration tests, audit, data provenance, backups/restore, security scan, export and deletion policy, accessible core flows.

**P1 — One complete workflow per domain:** each domain must support create/read/update, validation, search/filter, export, activity log, source provenance, and negative authorization tests.

**P2 — Real data and institutions:** one contracted data source and one pilot partner per domain, with data access/legal basis and agreed KPI baseline.

**P3 — AI assistance:** start with NEXORA research/learning assistant and low-risk summarization; evaluate citations and unsupported-claim refusal before release.

**P4 — Sector predictive models:** only after sufficient representative data, validation, bias review, and domain expert sign-off.

**P5 — Advanced enterprise and mobile:** SSO, webhooks, API marketplace, native mobile if PWA limitations are proven, offline sync conflict resolution, advanced digital twins.

Never use a feature count as a quality metric. Prefer fewer complete workflows with verified value over a long catalogue of inactive features.

## 15. Tooling workflow recommendation for this repository

Use Google Antigravity as the primary implementation environment because this repository needs coordinated edits across frontend, backend, SQL, Docker, tests and documentation, plus visual browser verification. Start in Plan/Review mode, require a repo map and proposed diff, then implement only one milestone. Use its browser workflow to exercise localhost, inspect console/network failures and save screenshots when that capability is available on the installed surface/account.

Use OpenAI Codex as a separate reviewer after each milestone: ask it to review the actual diff, threat model, migrations, test gaps and acceptance criteria. Do not let two agents edit the same migration or file simultaneously. The human owner approves migrations, secrets, data transfers, production changes and deployments.

Tool choice does not certify the code. A green agent summary is not evidence; require executed commands, artifacts, test logs and a human review.
