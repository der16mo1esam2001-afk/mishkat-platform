# سجل مصادر البيانات — نسخة تأسيسية

تاريخ مراجعة الروابط والمراجع: 13 نوفمبر 2026. الإدراج في هذا السجل يعني أن المصدر عُثر عليه في القنوات الرسمية، ولا يعني أن كل موصل برمجي اكتمل أو أن كل مجموعة بيانات حصلت على ترخيصها النهائي.

| النطاق | المصدر | طبيعة البيانات | الوصول/الاعتماد | القيود المهمة |
|---|---|---|---|---|
| VITALIS | WHO Data / World Health Data Hub | مؤشرات صحية مجمعة | بوابة البيانات وشروط WHO | ليست سجلات مرضى؛ تحقق من شروط كل مجموعة ونسخة الواجهة البرمجية الحالية |
| VITALIS | PhysioNet MIMIC-IV | سجلات سريرية بحثية منزوعة الهوية | اعتماد وتدريب واتفاقية استخدام | ليس بديلاً عن مستشفى محلي ولا عن المراجعة السريرية |
| AQUANEX | WRI Aqueduct 4.0 | مؤشرات مخاطر مائية مكانية وسيناريوهات | تنزيل بعد التسجيل؛ CC BY 4.0 مع نسبة WRI | تحديثات دورية غير لحظية؛ لا يمثل قياسات تسرب أو جودة ميدانية |
| AQUANEX | FAO AQUASTAT | إحصاءات المياه والزراعة المائية | بوابة/تنزيل | مستوى التغطية والتحديث يختلف حسب المؤشر |
| AGRONEX | FAOSTAT API | إحصاءات الزراعة والغذاء | API إنتاج موثق بتدفق مصادقة | يجب طلب الرمز واتباع شروط المصدر؛ بيانات دولية لا تمثل مزرعة بعينها |
| AGRONEX | FAO WaPOR v3 | بيانات الاستشعار عن بعد وإنتاجية المياه | API V3 لا يتطلب رمزاً بحسب وثائق FAO المنشورة | تحقق من تغطية المنطقة والدقة والفترة قبل أي توصية حقلية |
| AGRONEX / ENERGIS | NASA POWER Daily API | سلاسل يومية للطقس والإشعاع | API عامة بنقطة latitude/longitude؛ مجتمع AG للزراعة وRE للإشعاع الشمسي | بيانات شبكية وليست قياس حساس/عداد؛ يحدد UTC صراحة وقد تختلف خلية الشبكة عن النقطة المدخلة |
| ENERGIS | Ember Data API | توليد الكهرباء والطلب والانبعاثات سنوياً/شهرياً | مفتاح API بالتسجيل | CC BY 4.0 مع النسبة؛ ليس SCADA أو قياساً لحظياً |
| NEXORA | UNESCO Institute for Statistics | مؤشرات التعليم والعلوم والثقافة | Data API وBulk Download | إحصاءات قطاعية وليست ملفات متعلمين؛ استخدم API الحالية لا SDMX القديمة المتوقفة |
| VITALIS / AQUANEX / AGRONEX / NEXORA | CAPMAS National Data Archive | إحصاءات مصرية للصحة والتعليم والزراعة والمرافق | فهرس وطني؛ يختلف حق الوصول لكل مجموعة | بعض السجلات متاحة كبيانات، وبعضها مرخص أو بلا ملفات قابلة للتنزيل؛ تحقق من كل مجموعة قبل الاستخدام |
| ENERGIS | NREA Annual Report 2024 | إحصاءات الطاقة المتجددة المصرية | تقرير رسمي PDF | سنوي/تاريخي وليس بيانات عدادات حية |
| AQUANEX | MWRI institutional systems | نظم GIS وبيانات تشغيلية مؤسسية محتملة | شراكة مؤسسية مطلوبة | الإعلان الرسمي عن الأنظمة لا يعني أن البيانات التشغيلية منشورة أو مفتوحة |

## روابط رسمية

- WHO Data: https://data.who.int/
- WHO dataset terms: https://data.who.int/about/data/terms-and-conditions
- WHO AI research oversight: https://www.who.int/publications/i/item/9789240124073
- PhysioNet MIMIC-IV: https://physionet.org/content/mimiciv/
- WRI Aqueduct FAQ: https://www.wri.org/aqueduct/faq
- WRI Aqueduct 4.0 data and methodology: https://github.com/wri/Aqueduct40
- FAO AQUASTAT: https://www.fao.org/aquastat/en/
- FAOSTAT API: https://www.fao.org/faostat/en/docs/redoc-static.html
- FAO WaPOR access: https://www.fao.org/in-action/remote-sensing-for-water-productivity/wapor-data-access/en
- NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- Ember API: https://ember-energy.org/data/api/
- UNESCO UIS resources: https://databrowser.uis.unesco.org/resources
- CAPMAS National Data Archive: https://metadata.capmas.gov.eg/en/index.php/catalog/
- Egypt NREA 2024 report announcement: https://nrea.gov.eg/en/Media/New/2975
- Egypt MWRI digital/GIS systems announcement: https://sis.gov.eg/en/media-center/news/minister-of-irrigation-follows-up-on-digital-transformation-efforts-in-ministry/

## موصلات الحزمة الحالية

- NASA POWER: موصل فعلي في `POST /api/v1/connectors/nasa-power/fetch`، يتطلب رمز مستخدم محلي أو JWT ووجود الخادمين وقواعد البيانات. يتم الحفظ في قاعدة النطاق المختار فقط: AG إلى AGRONEX وRE إلى ENERGIS.
- المصادر الأخرى: مدرجة في سجل الأدلة داخل API، لكن موصل الاستيراد والتحويل والحفظ لكل مصدر لم يكتمل في الإصدار الحالي. لا تعرض الواجهة البيانات وكأنها استُوردت.
