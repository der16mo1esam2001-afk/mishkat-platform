# سجل الخصائص والتطوير — MISHKAT

هذا سجل فرص التطوير. لا يعني إدراج خاصية أنها منفذة. يجب إنشاء issue/acceptance criteria لكل ميزة قبل التطوير.

## P0 — قبل أي تجربة خارج فريق التطوير

- هوية إنتاجية OIDC/Supabase Auth كاملة في الواجهة والخادم، انتهاء/تجديد الجلسات، MFA عند الحاجة.
- عزل حسابات المستخدمين والمؤسسات عبر RLS واختبارات A/B في قواعد البيانات الخمس.
- معالجة مركزية للأخطاء، correlation IDs، logs منقحة، مراقبة جاهزية كل DB.
- migrations قابلة للتكرار والاختبار على PostgreSQL/PostGIS فعلي.
- secret scanning، dependency audit، container scan، SAST، backups واستعادة مثبتة.
- سجل مصدر بيانات وترخيص ومنشأ لكل قيمة تعرض للمستخدم.
- تصدير وحذف واحتفاظ وموافقات قابلة للتدقيق حسب كل مجال.
- سياسة الخصوصية وشروط الاستخدام ومراجعة قانونية للبلدان المستهدفة.

## P1 — إكمال الوظائف الأساسية لكل قطاع

- إدارة الملفات والعناصر والمواقع والمزارع والعدادات والأصول.
- البحث والتصفية والترتيب والتقسيم إلى صفحات.
- نماذج إدخال وتحديث وحذف مع تحقق خادمي وقيود DB.
- سجلات تشغيل/حالات/تنبيهات/مهام/أوامر عمل حسب المجال.
- سجل تدقيق كامل لكل عمليات الإنشاء والتعديل والتصدير والموافقات.
- مركز موحد لحالة مصادر البيانات والاستيراد والفشل وإعادة المحاولة.
- لوحة مؤشرات لا تعرض إلا بيانات لها source + timestamp + unit + quality label.

## P2 — تجارب ميدانية وموصلات بيانات

- مصدر مرخص ومختبر لكل مجال.
- تكامل WHO/PhysioNet وفق الأهلية والاتفاقيات، دون نشر البيانات الفردية.
- AQUANEX: جهة مياه توفر GIS وقياسات ضغط/تدفق وعينات مع سجل معايرة.
- AGRONEX: مزرعة تجريبية مع crop season وsoil tests وirrigation logs وharvest outcomes.
- ENERGIS: منشأة توفر قراءات عداد تاريخية مع وحدات وفواصل زمنية وتعرفة.
- NEXORA: مصدر تعليمي مرخص ومجموعة متعلمين تجريبية وموافقة مناسبة.
- جودة بيانات: completeness, freshness, validity, duplicate rate, missingness, outlier review.

## P3 — ذكاء اصطناعي مساعد منخفض المخاطر

- AI Gateway متعدد الموردين مع أسرار خادمية.
- RAG بمحتوى مرخص ومراجع قابلة للتحقق.
- سجل prompts/models والتكلفة والوقت والإصدارات.
- Eval sets واختبارات citation correctness وunsupported answer refusal.
- مساعد بحثي/تعليمي أولاً، وملخصات تشغيلية مع مراجع.
- موافقة منفصلة قبل إرسال أي بيانات شخصية إلى مزود خارجي.

## P4 — نماذج قطاعية تنبؤية

- VITALIS: تنبؤ/مساندة سريرية فقط بعد شريك سريري، موافقات أخلاقية، وتحقق خارجي.
- AQUANEX: anomaly/leak triage مع بيانات حساسات معروفة وground truth من الفحص الميداني.
- AGRONEX: crop health/yield forecast مع بيانات مواسم متعددة واختبار مكاني/زمني مستقل.
- ENERGIS: load forecasting/asset anomalies مع baseline ومقاييس خطأ واضحة.
- NEXORA: adaptive path and mastery models مع تجارب تعلم وضوابط انحياز.
- كل نموذج له Model Card وversion وtraining provenance وevaluation report وrollback.

## P5 — وظائف مؤسسية متقدمة

- Organizations/teams, RBAC + ABAC, SSO, invitation and lifecycle management.
- Webhooks موقعة مع replay protection، API keys محددة النطاق، quotas وdeveloper portal.
- Workflow approvals، SLA/escalations، case management وtask assignment.
- Notification center بقنوات قابلة للضبط.
- Multi-region deployments and data residency controls.
- Observability وSLO dashboards، incident management، cost attribution وFinOps.

## P6 — تطبيقات وأجهزة واتصال بالعالم الحقيقي

- PWA offline shell مع conflict-safe sync عند الحاجة.
- تطبيق Flutter/React Native إذا أثبتت احتياجات الكاميرا/المستشعرات/الإشعارات/العمل دون اتصال الحاجة له.
- Wearables في الصحة بعد الموافقة والحوكمة الطبية.
- Sensors/IoT في المياه والزراعة والطاقة مع device registry/calibration/security.
- Digital twins بعد وجود بيانات تشغيلية مستمرة ومعمارية مكانية موثوقة.
- تكامل OT/SCADA للقراءة فقط في البداية؛ أي كتابة تحتاج شبكة منفصلة ومراجعة أمن صناعي وموافقة مشغل.

## قواعد الاختيار

- الأولوية لخاصية تقلل خطراً أو تكلفة أو زمناً أو تحسن نتيجة مثبتة.
- لا تطور AI قبل توافر البيانات والـ baseline والاختبار.
- لا تبنِ سوق تطبيقات أو token economy أو social feed لمجرد زيادة حجم المنتج.
- اجعل كل feature flag قابلاً للإيقاف إذا فشل التكامل أو ظهر أثر جانبي.
