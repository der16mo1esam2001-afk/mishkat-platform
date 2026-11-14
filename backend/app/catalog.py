from datetime import date

WORKSPACES = [
    {
        "id": "vitalis", "code": "VITALIS AI", "name_ar": "الذكاء الصحي الوقائي", "name_en": "Preventive Health Intelligence",
        "description_ar": "تنظيم المعلومات الصحية والمتابعة الوقائية ودعم القرار السريري الموثق تحت إشراف المختصين.",
        "icon": "heart-pulse", "color": "mint", "stage": "concept", "safety": "clinical_review_required",
        "database": "vitalis", "tables": ["patient_profiles", "encounters", "clinical_observations", "care_plans", "consent_records"]
    },
    {
        "id": "aquanex", "code": "AQUANEX", "name_ar": "استخبارات المياه", "name_en": "Water Intelligence",
        "description_ar": "تحليل موارد المياه وجودتها وأصول الشبكات والقياسات الميدانية والمخاطر الجغرافية.",
        "icon": "droplets", "color": "blue", "stage": "concept", "safety": "operator_approval_required",
        "database": "aquanex", "tables": ["water_assets", "telemetry_readings", "water_samples", "water_alerts", "work_orders"]
    },
    {
        "id": "agronex", "code": "AGRONEX", "name_ar": "الذكاء الزراعي والأمن الغذائي", "name_en": "Agricultural Intelligence",
        "description_ar": "ربط بيانات المحاصيل والطقس والتربة والري وصور الاستشعار عن بعد والإنتاج.",
        "icon": "sprout", "color": "green", "stage": "concept", "safety": "agronomist_review_required",
        "database": "agronex", "tables": ["farms", "plots", "crop_cycles", "soil_samples", "weather_observations", "yield_records"]
    },
    {
        "id": "energis", "code": "ENERGIS", "name_ar": "استخبارات الطاقة", "name_en": "Energy Intelligence",
        "description_ar": "تحليل الاستهلاك والتوليد والتنبؤ بالأحمال وكفاءة المعدات والطاقة المتجددة.",
        "icon": "zap", "color": "amber", "stage": "concept", "safety": "operator_approval_required",
        "database": "energis", "tables": ["energy_sites", "meters", "meter_readings", "generation_records", "forecasts", "anomalies"]
    },
    {
        "id": "nexora", "code": "NEXORA", "name_ar": "التعلم والذكاء المعرفي الشخصي", "name_en": "Learning & Knowledge Intelligence",
        "description_ar": "مسارات تعلم تكيفية ومحتوى موثق وتقييم للإتقان والاحتفاظ بالمعرفة.",
        "icon": "graduation-cap", "color": "violet", "stage": "concept", "safety": "learner_protection_required",
        "database": "nexora", "tables": ["learner_profiles", "learning_goals", "learning_resources", "learning_paths", "assessments", "assessment_attempts", "mastery_records"]
    },
]

SOURCES = [
    {"id":"who_gho","domain":"vitalis","name":"WHO Global Health Observatory","publisher":"World Health Organization","type":"aggregate_indicators","access":"public_api","url":"https://data.who.int/","license":"WHO dataset terms; generally CC BY 4.0 unless otherwise stated","update":"Dataset and release-dependent","status":"catalogued","notes":"Prefer current World Health Data Hub/Datadot interfaces. Legacy GHO OData was marked for deprecation; verify the specific current API before implementation. Aggregate indicators only, not patient records."},
    {"id":"physionet_mimic","domain":"vitalis","name":"MIMIC-IV","publisher":"PhysioNet / MIT Lab for Computational Physiology","type":"deidentified_research_dataset","access":"credentialed_access","url":"https://physionet.org/content/mimiciv/","license":"Credentialing, training and data use agreement required","update":"Dataset release-dependent","status":"access_restricted","notes":"Research dataset; not a substitute for local clinical validation or clinical data authorization."},
    {"id":"wri_aqueduct","domain":"aquanex","name":"Aqueduct 4.0","publisher":"World Resources Institute","type":"water_risk_geospatial","access":"download_after_registration","url":"https://www.wri.org/aqueduct/faq","license":"CC BY 4.0 with attribution per WRI terms","update":"Version / release-dependent","status":"catalogued","notes":"Strategic water-risk prioritization. Composite risk scores are not direct real-time measurements."},
    {"id":"fao_aquastat","domain":"aquanex","name":"FAO AQUASTAT","publisher":"Food and Agriculture Organization of the United Nations","type":"water_statistics","access":"public_portal_or_download","url":"https://www.fao.org/aquastat/en/","license":"Check dataset-specific reuse terms","update":"Dataset-dependent","status":"catalogued","notes":"Country-level water and agriculture statistics; not utility telemetry."},
    {"id":"fao_wapor","domain":"agronex","name":"FAO WaPOR v3","publisher":"FAO","type":"remote_sensing_water_productivity","access":"public_api_no_token_for_v3","url":"https://www.fao.org/in-action/remote-sensing-for-water-productivity/wapor-data-access/en","license":"Review source-specific conditions and attribution","update":"Product and geography-dependent","status":"catalogued","notes":"Remote-sensing water productivity layers; validate coverage and resolution before local farm claims."},
    {"id":"faostat","domain":"agronex","name":"FAOSTAT API","publisher":"FAO","type":"agriculture_food_statistics","access":"official_api_authentication_flow","url":"https://www.fao.org/faostat/en/docs/redoc-static.html","license":"Review FAO dataset terms and attribution","update":"FAOSTAT release-dependent","status":"credential_required","notes":"Production API documents an authentication flow; do not assume anonymous access."},
    {"id":"nasa_power","domain":"agronex,energis","name":"NASA POWER Daily API","publisher":"NASA Langley Research Center","type":"meteorology_solar_resource","access":"public_api","url":"https://power.larc.nasa.gov/docs/services/api/temporal/daily/","license":"NASA dataset-specific terms; cite source and parameters","update":"Daily series from 1981 to near-real-time subject to product latency","status":"ready_to_connect","notes":"Point series require latitude, longitude, date interval, supported community/parameter selection, and explicit UTC time standard. The selected grid cell is not a point sensor. NASA weather/solar resource data is not electricity meter data."},
    {"id":"ember","domain":"energis","name":"Ember Data API","publisher":"Ember","type":"electricity_generation_demand_emissions","access":"api_key_registration","url":"https://ember-energy.org/data/api/","license":"CC BY 4.0 with attribution and no additional legal/technical restrictions","update":"Monthly / yearly release-dependent","status":"credential_required","notes":"Open electricity statistics; not live SCADA or substation telemetry."},
    {"id":"uis","domain":"nexora","name":"UNESCO Institute for Statistics","publisher":"UNESCO UIS","type":"education_science_statistics","access":"data_api_and_bulk_download","url":"https://databrowser.uis.unesco.org/","license":"Check dataset-specific terms and attribution","update":"Release-dependent","status":"catalogued","notes":"Education and science indicators; not individual learner records or textbook content."},
    {"id":"capmas_nda","domain":"vitalis,aquanex,agronex,nexora","name":"CAPMAS National Data Archive","publisher":"Central Agency for Public Mobilization and Statistics (Egypt)","type":"egypt_national_statistics","access":"catalogue_access_varies","url":"https://metadata.capmas.gov.eg/en/index.php/catalog/","license":"Dataset-level; some entries are licensed and some list no downloadable data","update":"Catalog and datasets update independently","status":"catalogued","notes":"Egyptian health, education, agriculture, utilities and other statistical collections. Review each dataset's access and license before download or reuse; aggregate statistics are not individual records."},
    {"id":"nrea_annual","domain":"energis","name":"Egypt NREA Annual Report 2024","publisher":"New and Renewable Energy Authority (Egypt)","type":"national_renewable_energy_statistics","access":"official_report_pdf","url":"https://nrea.gov.eg/en/Media/New/2975","license":"Review report-specific terms and attribution","update":"Annual publication","status":"catalogued","notes":"Official annual report with renewable capacity and generation statistics; historical/annual reporting, not live meter or grid telemetry."},
    {"id":"mwri_partner","domain":"aquanex","name":"Egypt Ministry of Water Resources and Irrigation — institutional systems","publisher":"Ministry of Water Resources and Irrigation (Egypt)","type":"institutional_gis_and_operational_data","access":"institutional_partner_required","url":"https://sis.gov.eg/en/media-center/news/minister-of-irrigation-follows-up-on-digital-transformation-efforts-in-ministry/","license":"Agreement and authorization required from data owner","update":"Depends on ministry systems and agreements","status":"partner_required","notes":"Public notice describes ministry GIS applications/databases; it is not an open data feed. Operational network and sensor data require formal partnership and permission."},
]

SOURCE_AS_OF = date(2026, 11, 13).isoformat()
