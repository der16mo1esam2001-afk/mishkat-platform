# سجل ومصفوفة موصلات البيانات — Data Connector Status Matrix
**تاريخ التحقق والتسجيل:** 14 نوفمبر 2026  
**الإصدار:** 0.3.0  
**إطار الحوكمة:** Science & Data Provenance Framework  

---

## 1. جدول حالة الموصلات الستة الموحدة

| رمز الموصل | اسم المصدر والناشر | القطاع المستهدف | طريقة الوصول | حالة الموصل الحالية | حالة الاختبار الحي | شروط الاستخدام والترخيص |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `nasa_power` | **NASA POWER Daily API**<br>NASA Langley Center | AGRONEX & ENERGIS | REST API (JSON) | **CONNECTED** | **ناجح حياً** (HTTP 200)<br>تم جلب بيانات حية | Public Domain / Open NASA Policy<br>مع الاحتفاظ بالإسناد |
| `who_gho` | **WHO Global Health Observatory**<br>World Health Organization | VITALIS | OData v4 REST API | **CONNECTED** | **ناجح حياً** (HTTP 200)<br>استرجاع المؤشرات القومية | CC BY-NC-SA 3.0 IGO<br>استخدام غير تجاري وبحثي |
| `aqueduct_aquastat` | **WRI Aqueduct 4.0 & AQUASTAT**<br>WRI & FAO | AQUANEX | Catalogued GIS/Tabular | **CATALOGUED** | فحص العقد واختبار المحاكاة | CC BY 4.0<br>إسناد المصدر |
| `faostat_wapor` | **FAOSTAT & FAO WaPOR**<br>FAO Statistics Division | AGRONEX | REST API & Bulk SDMX | **CATALOGUED** | فحص العقد واختبار المحاكاة | CC BY-NC-SA 3.0 IGO<br>إحصاءات إنتاج زراعي |
| `ember_energy` | **Ember Electricity Review**<br>Ember Climate | ENERGIS | REST API (API Key) | **CREDENTIALS_MISSING** | فحص العقد مسجل | CC BY 4.0<br>يتطلب مفتاح `EMBER_API_KEY` |
| `unesco_uis` | **UNESCO Institute for Statistics**<br>UNESCO UIS Data Centre | NEXORA | SDMX API & Open Data | **CATALOGUED** | فحص العقد واختبار المحاكاة | CC BY-SA 3.0 IGO<br>مؤشرات التعليم والمهارات |

---

## 2. معايير سلامة البيانات ومصداقيتها (Data Integrity Rules)

1. **التمييز العلمي الإلزامي:**
   - `measured`: قياس فعلي مباشر من حساس أو عداد أو عينة مختبر.
   - `self_reported`: إدخال ذاتي مصادق عليه.
   - `official_aggregate`: إحصاء قومي أو إقليمي مجمع (مثل بيانات WHO أو FAOSTAT أو UNESCO).
   - `remote_sensing`: بيانات شبكية مستشعرة عن بعد (مثل NASA POWER أو WaPOR).
   - `forecast`: توقع رياضي مرتبط بنطاق عدم يقين (Confidence Interval).

2. **قاعدة حظر الأصفار الوهمية:**
   - حظر تحويل القيم المفقودة إلى أصفار (`-999` في NASA POWER تحفظ كـ `null` حصرياً).

3. **سلسلة الحيازة والمنشأ (Data Provenance):**
   - كل استدعاء يسجل: معرف الاستيراد `ingestion_run_id`، بصمة البيانات `provenance_hash` عبر خوارزمية SHA-256، وقت الاسترجاع بدقة UTC، وترخيص المصدر.
