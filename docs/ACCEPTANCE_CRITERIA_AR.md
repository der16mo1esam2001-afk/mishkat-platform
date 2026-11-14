# معايير القبول واختبارات التحقق

## البوابة المشتركة
- [ ] `GET /api/v1/health/live` يعيد HTTP 200.
- [ ] قواعد البيانات الخمس تتصل بالخادم من داخل شبكة Docker.
- [ ] قواعد البيانات ليست منشورة على منافذ عامة.
- [ ] لا يظهر أي سر في الملفات الثابتة أو JavaScript المرسل للمتصفح.
- [ ] لا يمكن الوصول لأي API محمية من دون Bearer token صالح.
- [ ] يرفض الخادم رمزاً منتهياً أو بتوقيع أو issuer أو audience غير صحيح.
- [ ] كل جدول يحتوي بيانات مستخدم عليه RLS ENABLE وFORCE وسياسة مناسبة.
- [ ] اختبار مستخدم A لا يقرأ أو يعدل بيانات مستخدم B في كل جدول.
- [ ] تدقيق سجل أحداث كل نطاق.
- [ ] اختبار استعادة قاعدة بيانات من نسخة احتياطية.

## موصل NASA POWER
- [ ] رفض الإحداثيات خارج النطاق.
- [ ] رفض فترة أكبر من الحد البرمجي المعلن.
- [ ] رفض بارامترات غير مدعومة.
- [ ] التعامل مع HTTP failure وtimeouts وJSON غير صالح.
- [ ] حفظ المصدر والوقت والوحدة والإحداثيات والقيمة الخام.
- [ ] الحفاظ على NULL/رمز missing وعدم تحويله إلى صفر.
- [ ] إثبات أن سجل AGRONEX لا يكتب داخل ENERGIS والعكس.

## معايير قبول قطاعية

### VITALIS
- [ ] مصدر صحي مصرح به وسجل موافقات واضح.
- [ ] استخدام معرفات مستعارة وتقليل حقول التعريف.
- [ ] توافق موارد التبادل الصحي مع FHIR profile محدد عند بدء التكامل.
- [ ] مراجعة سريرية وأخلاقية قبل استخدام أي تنبؤ سريري.

### AQUANEX
- [ ] أصل مائي له معرف جغرافي موثق.
- [ ] قياسات لها وحدة ومصدر ووقت ومعايرة.
- [ ] اختبار أحداث تسرب مؤكدة منفصلة عن الإنذارات المحتملة.
- [ ] لا يوجد تحكم تشغيلي مباشر من النظام.

### AGRONEX
- [ ] مزارع وقطع ومحصول ودورة زراعية مسجلة.
- [ ] مصدر الطقس/الاستشعار مرتبط بالموقع والفترة والدقة.
- [ ] نتائج التوقع تختبر على موسم أو مزرعة خارج مجموعة التدريب.
- [ ] توصيات وقاية المحاصيل تراجع من مختص.

### ENERGIS
- [ ] قراءات عداد مع نوع العداد والوحدة والفترة الزمنية.
- [ ] التمييز بين قياس الشبكة وإحصاءات Ember وبيانات NASA المناخية.
- [ ] مقارنة التنبؤ بخط أساس معلن وحساب خطأ التوقع.
- [ ] عدم إرسال أوامر تحكم إلى المعدات.

### NEXORA
- [ ] محتوى تعليمي له ناشر وترخيص ورابط ومعلومات إصدار.
- [ ] مسار تعلم يحتوي أهدافاً وأنشطة وتقييمات.
- [ ] تقاس المعرفة قبل وبعد التعلم والاحتفاظ لاحقاً.
- [ ] اختبار الوصول لذوي الإعاقة واللغة العربية RTL ومقاسات الهاتف.

## مخرجات الاختبار
لكل تشغيل، احفظ: نسخة الكود، نسخة المخطط، البيئة، الأمر الفعلي، عدد الاختبارات المنفذة والناجحة والفاشلة، الأدلة، القيود، واسم المراجع. لا تسجل اختباراً على أنه ناجح إذا لم يُشغل.

## NEXORA pilot additions in 0.2.0
- [ ] Policy version is fetched from the API and submitted with explicit consent.
- [ ] Adult-only pilot is clearly identified as self-attestation, not identity/age verification.
- [ ] Consent creation is recorded append-only; application role cannot update/delete the consent history table.
- [ ] Revoking consent blocks new goal/path writes and goal status updates.
- [ ] Export endpoint returns only the authenticated owner's profile, goals, learning paths and consent history.
- [ ] Export route is covered by owner-scoped authorization tests.
- [ ] Existing records are retained after withdrawal until an approved retention/deletion workflow is implemented and disclosed.

## CI acceptance
- [ ] GitHub Actions workflow runs on pull requests and protected branches.
- [ ] Python compilation, JavaScript syntax, automated tests and Compose configuration checks pass.
- [ ] Bandit and pip-audit pass with findings reviewed and triaged.
- [ ] Container build succeeds and the image runs as a non-root user.
- [ ] CI status is visible and required before merging to the release branch.

These are acceptance requirements, not claims that PostgreSQL, RLS, CI or container runtime validation has already passed in this environment.
