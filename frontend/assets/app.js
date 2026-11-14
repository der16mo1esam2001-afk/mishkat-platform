(() => {
  const API = '/api/v1';
  const state = { token: sessionStorage.getItem('mishkat_dev_token') || '', activeView: 'overview', activeModule: null, db: {}, toastTimer: null, nexoraProfile: null, nexoraConsentPolicy: null };
  const modules = {
    vitalis: { code:'VITALIS AI', title:'الذكاء الصحي الوقائي', en:'PREVENTIVE HEALTH INTELLIGENCE', icon:'✚', color:'mint', desc:'منظومة لتنظيم السجلات الصحية المصرح بها، ومتابعة الرعاية الوقائية، وتحليل مؤشرات الأداء. لا تقدم تشخيصاً مستقلاً ولا وصفات علاجية.', capabilities:['ملف صحي طولي بمعرف مستعار','زيارات وملاحظات صحية منظمة','متابعة خطط الرعاية والمواعيد','مؤشرات وقاية وتحليلات مجمعة','استرجاع أدلة طبية بمراجعها','موافقات وسجل تدقيق'], sources:['WHO Global Health Observatory','PhysioNet MIMIC-IV'], safety:'البيانات الصحية حساسة. لا تستخدم بيانات مرضى حقيقية قبل الأساس القانوني والموافقة والاعتماد الأخلاقي والشراكة السريرية.' },
    aquanex: { code:'AQUANEX', title:'استخبارات المياه', en:'WATER INTELLIGENCE', icon:'≈', color:'blue', desc:'طبقة تحليل مكاني وتشغيلي لموارد المياه وجودتها وأصول الشبكات والقياسات الميدانية. مؤشرات المخاطر لا تُعامل كقياسات لحظية.', capabilities:['سجل الأصول والشبكات الجغرافي','قياسات التدفق والضغط والحساسات','إدارة عينات جودة المياه والمختبر','رصد الشذوذ والتنبيهات','أوامر العمل والصيانة','تحليل المخاطر المكانية'], sources:['WRI Aqueduct 4.0','FAO AQUASTAT'], safety:'لا يصدر النظام أوامر تحكم للمضخات أو الصمامات. يتطلب ذلك نظام تحكم صناعي معتمد وموافقة مشغل ومفاتيح أمان مستقلة.' },
    agronex: { code:'AGRONEX', title:'الذكاء الزراعي والأمن الغذائي', en:'AGRICULTURAL INTELLIGENCE', icon:'❋', color:'green', desc:'منظومة لإدارة الأراضي والمحاصيل والتربة والري والطقس والإنتاج، مع فصل بيانات الأقمار الصناعية عن القياسات الحقلية.', capabilities:['ملف رقمي للمزرعة والقطعة','دورات المحاصيل ومراحل النمو','عينات التربة والتحاليل','الطقس والاستشعار عن بعد','تخطيط الري والاستهلاك','توقع الإنتاج ومقارنة الحصاد'], sources:['FAOSTAT API','NASA POWER Daily API','FAO WaPOR v3'], safety:'توصيات أمراض النبات احتمالية حتى يراجعها مختص. لا تُصدر تعليمات مبيدات أو معاملات كيميائية دون اعتماد محلي.' },
    energis: { code:'ENERGIS', title:'استخبارات الطاقة', en:'ENERGY INTELLIGENCE', icon:'ϟ', color:'amber', desc:'منصة لتحليل استهلاك الطاقة وإنتاج المصادر المتجددة والتنبؤ بالأحمال وكفاءة المعدات، مع تمييز الإحصاءات العامة من بيانات العدادات.', capabilities:['سجل المواقع والأصول والعدادات','قراءات العدادات مع جودة القياس','تحليل إنتاج الطاقة المتجددة','توقع الأحمال بنطاق عدم يقين','اكتشاف الشذوذ ومراجعة الأعطال','تحليل الكفاءة والتكلفة'], sources:['Ember Data API','NASA POWER Daily API','Egypt NREA reports'], safety:'NASA POWER يقيس متغيرات الطقس والإشعاع وليس الكهرباء المستهلكة. لا يتم التحكم في الشبكات أو المعدات من هذه المنصة.' },
    nexora: { code:'NEXORA', title:'التعلم والذكاء المعرفي الشخصي', en:'LEARNING & KNOWLEDGE INTELLIGENCE', icon:'✧', color:'violet', desc:'نظام تعلم يتكيف مع المتعلم، ويربط المحتوى بالمصادر والاختبارات ومؤشرات الإتقان والاحتفاظ، مع احترام ترخيص المواد التعليمية.', capabilities:['ملف المتعلم والأهداف والمهارات','مسارات تعلم تكيفية','مساعد تعلم مع استشهادات','اختبارات تشخيصية وتكوينية وختامية','قياس الإتقان والاحتفاظ','محتوى متعدد اللغات وإتاحة رقمية'], sources:['UNESCO Institute for Statistics','Licensed educational resources'], safety:'لا تُخزن بيانات القاصرين قبل موافقة ولي الأمر أو المؤسسة والسياسات القانونية اللازمة. إحصاءات التعليم العامة ليست سجلات طلاب.' }
  };
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => [...root.querySelectorAll(s)];
  const arabicDate = new Intl.DateTimeFormat('ar-EG', {dateStyle:'medium'});

  function showToast(message, error=false) {
    const el = $('#toast'); el.textContent = message; el.classList.toggle('error', error); el.classList.add('show');
    clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => el.classList.remove('show'), 4200);
  }
  async function api(path, options={}) {
    const headers = {'Content-Type':'application/json', ...(options.headers || {})};
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    const response = await fetch(`${API}${path}`, {...options, headers});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail ? (typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)) : `HTTP ${response.status}`);
    return body;
  }
  function navigate(view) {
    if (modules[view]) { state.activeModule = view; renderModule(view); $('#breadcrumbCurrent').textContent = modules[view].title; }
    else { state.activeModule = null; $('#breadcrumbCurrent').textContent = view === 'overview' ? 'نظرة عامة' : view === 'sources' ? 'مصادر البيانات والأدلة' : 'المعمارية والأمان'; }
    state.activeView = view;
    $$('.view').forEach(el => el.classList.remove('active'));
    const section = modules[view] ? $('#view-module') : $(`#view-${view}`);
    section?.classList.add('active');
    $$('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.view === view));
    $('#sidebar').classList.remove('open');
    window.scrollTo({top:0, behavior:'smooth'});
  }
  function renderModule(key) {
    const m = modules[key];
    $('#moduleKicker').textContent = `${m.en} / ${Object.keys(modules).indexOf(key)+1}`;
    $('#moduleTitle').textContent = m.code;
    $('#moduleDescription').textContent = m.desc;
    $('#moduleIcon').textContent = m.icon;
    $('#moduleDatabase').textContent = `قاعدة PostgreSQL مستقلة: ${key}`;
    $('#moduleSafety').textContent = m.safety;
    $('#moduleCapabilities').replaceChildren(...m.capabilities.map((cap, i) => {
      const item = document.createElement('div'); item.className='capability-item';
      const n=document.createElement('span'); n.textContent=String(i+1).padStart(2,'0');
      const t=document.createElement('strong'); t.textContent=cap; item.append(n,t); return item;
    }));
    $('#moduleSources').replaceChildren(...m.sources.map(source => {const el=document.createElement('span');el.className='source-chip';el.textContent=source;return el;}));
    const nasaEligible = key === 'agronex' || key === 'energis';
    $('#nasaAction').hidden = !nasaEligible;
    $('#moduleDataNote').textContent = key === 'agronex' || key === 'energis'
      ? 'يمكن جلب بيانات NASA POWER اليومية بعد الاتصال بالـ API. البيانات تمثل متغيرات مناخية/شمسية لشبكة جغرافية وليست قياسات مزرعة أو عداد كهرباء.'
      : 'مصادر القطاع مُدرجة كمرجع. يلزم تهيئة الترخيص أو بيانات الوصول المناسبة قبل الاستيراد.';
    const status = state.db[key] || 'لم يتم التحقق';
    $('#moduleDbState').textContent = `حالة الاتصال: ${status === 'connected' ? 'متصل' : status}`;
    $('#nexoraWorkspace').hidden = key !== 'nexora';
    $('#moduleActivityPanel').hidden = false;
    if (state.token) {
      loadModuleActivity(key);
      if (key === 'nexora') loadNexoraWorkspace();
    }
  }
  async function startLocalSession() {
    try {
      const data = await fetch(`${API}/auth/dev-token`, {method:'POST'}).then(async r => {const b=await r.json();if(!r.ok)throw new Error(b.detail || `HTTP ${r.status}`);return b;});
      state.token = data.access_token; sessionStorage.setItem('mishkat_dev_token', state.token);
      $('#authStatus').textContent = 'جلسة تطوير محلية';
      showToast('بدأت جلسة محلية محدودة للتطوير. لا تستخدمها للإنتاج.');
      await loadSources(); await refreshDbStatus();
    } catch (e) { showToast(`تعذر بدء الجلسة: ${e.message}. شغّل خادم MISHKAT أولاً.`, true); }
  }
  async function refreshDbStatus() {
    try {
      const data = await fetch(`${API}/health/ready`).then(async r => {const b=await r.json();if(!r.ok)throw new Error(`HTTP ${r.status}`);return b;});
      state.db = data.databases || {};
      const connected = Object.values(state.db).filter(v => v === 'connected').length;
      $('#dbState').textContent = `${connected} من 5 متصلة`;
      $('#lastCheck').textContent = `آخر فحص: ${new Date().toLocaleTimeString('ar-EG',{hour:'2-digit',minute:'2-digit'})}`;
      $('#dbCount').textContent = `${connected}/5 متصلة`;
      if (state.activeModule) renderModule(state.activeModule);
      if (data.status !== 'ready') showToast('بعض قواعد البيانات غير متصلة. راجع إعداد Docker وقيم الاتصال.', true);
      return data;
    } catch (e) {
      $('#dbState').textContent = 'تعذر الوصول إلى API'; $('#lastCheck').textContent = 'خادم المنصة غير متاح';
      showToast('لم أستطع الاتصال بخادم المنصة. شغّل Docker Compose ثم أعد الفحص.', true);
      return null;
    }
  }
  function sourceStatusLabel(status) {
    return ({catalogued:'مدرج — لم يُستورد',ready_to_connect:'جاهز للاتصال',credential_required:'يتطلب اعتماداً',access_restricted:'وصول مقيد'})[status] || status;
  }
  async function loadSources() {
    if (!state.token) { showToast('ابدأ جلسة التطوير المحلية أولاً لتحميل السجل من API.', true); return; }
    try {
      const {items=[]} = await api('/evidence/sources');
      const tbody=$('#sourceRows'); tbody.replaceChildren();
      for (const source of items) {
        const tr=document.createElement('tr');
        const values=[source.name, source.domain.split(',').map(x=>x.toUpperCase()).join(' / '), source.access.replaceAll('_',' '), sourceStatusLabel(source.status)];
        for(const val of values){const td=document.createElement('td');td.textContent=val;tr.append(td);}
        const td=document.createElement('td');const a=document.createElement('a');a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='المصدر الرسمي ↗';td.append(a);tr.append(td);tbody.append(tr);
      }
      showToast(`تم تحميل ${items.length} مصادر من سجل المنصة. لم يتم استيراد كل هذه المصادر.`);
    } catch(e) { showToast(`تعذر تحميل سجل المصادر: ${e.message}`, true); }
  }
  function openNasaDialog() {
    if (!state.token) { showToast('ابدأ جلسة تطوير محلية قبل استيراد البيانات.', true); return; }
    const end = new Date(); end.setDate(end.getDate()-2);
    const start = new Date(end); start.setDate(start.getDate()-13);
    $('#endDate').value = end.toISOString().slice(0,10); $('#startDate').value = start.toISOString().slice(0,10);
    $('#nasaDialog').showModal();
  }
  async function fetchNasa(event) {
    event.preventDefault(); const button=$('#fetchNasa'); button.disabled=true; button.textContent='جارٍ الجلب والتحقق…';
    try {
      const isAgriculture = state.activeModule === 'agronex';
      const payload={latitude:Number($('#latitude').value),longitude:Number($('#longitude').value),start_date:$('#startDate').value,end_date:$('#endDate').value,parameters:isAgriculture?['T2M','PRECTOTCORR','RH2M']:['ALLSKY_SFC_SW_DWN'],community:isAgriculture?'AG':'RE'};
      const result=await api('/connectors/nasa-power/fetch',{method:'POST',body:JSON.stringify(payload)});
      const persisted=result.persistence || {};
      const savedDomain=Object.keys(persisted)[0] || 'النطاق';
      const savedCount=persisted[savedDomain];
      const summary=`استرجع NASA POWER ${result.record_count} سجلًا. حالة الحفظ في ${savedDomain.toUpperCase()}: ${savedCount===-1?'فشل':savedCount+' سجلًا'}.`;
      $('#nasaDialog').close(); showToast(summary, savedCount===-1);
      $('#moduleDataNote').textContent=`آخر استرجاع موثق من NASA POWER: ${result.retrieved_at}. عدد السجلات المسترجعة: ${result.record_count}. راجع تفاصيل الحفظ والتحذيرات في استجابة API.`;
      await refreshDbStatus();
    } catch(e) { showToast(`فشل الاستيراد: ${e.message}`, true); }
    finally { button.disabled=false; button.innerHTML='جلب البيانات وحفظها <span>↗</span>'; }
  }
  function safeText(value) { return value == null ? '—' : String(value); }
  function formatTimestamp(value) {
    if (!value) return '—';
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? 'تاريخ غير متاح' : d.toLocaleString('ar-EG', {dateStyle:'medium', timeStyle:'short'});
  }
  async function loadModuleActivity(domain) {
    try {
      const data = await api(`/modules/${domain}/activity?limit=8`);
      const ingestion = $('#ingestionActivity'); ingestion.replaceChildren();
      if (!data.ingestion_runs.length) {
        const p=document.createElement('p'); p.className='empty-cell'; p.textContent='لا توجد عمليات استيراد مسجلة لهذا المستخدم في هذا القطاع.'; ingestion.append(p);
      } else for (const item of data.ingestion_runs) {
        const row=document.createElement('article'); row.className='record-row';
        const title=document.createElement('strong'); title.textContent=`${item.source_id} · ${item.target_dataset}`;
        const meta=document.createElement('small'); meta.textContent=`${item.status} · ${item.records_saved}/${item.records_received} · ${formatTimestamp(item.requested_at)}`;
        row.append(title,meta); ingestion.append(row);
      }
      const models=$('#modelActivity'); models.replaceChildren();
      if (!data.models.length) {
        const p=document.createElement('p'); p.className='empty-cell'; p.textContent='لا توجد نماذج مسجلة. لا يعني ذلك أن نماذج غير مسجلة غير موجودة؛ هذا سجل النماذج المملوك للمستخدم فقط.'; models.append(p);
      } else for (const item of data.models) {
        const row=document.createElement('article'); row.className='record-row';
        const title=document.createElement('strong'); title.textContent=`${item.model_key} · ${item.model_version}`;
        const meta=document.createElement('small'); meta.textContent=`${item.status} · ${item.use_case}`;
        row.append(title,meta); models.append(row);
      }
    } catch (e) {
      showToast(`تعذر تحميل سجل النشاط: ${e.message}`, true);
    }
  }
  async function loadNexoraWorkspace() {
    try {
      const [profileData, consentPolicy] = await Promise.all([api('/nexora/profile'), api('/nexora/consent-policy')]);
      state.nexoraProfile = profileData.profile;
      state.nexoraConsentPolicy = consentPolicy;
      $('#nexoraConsentVersion').textContent = consentPolicy.policy_version;
      const profile = profileData.profile;
      $('#nexoraProfileState').textContent = profile ? `ملف محفوظ · ${profile.consent_status} · ${profile.locale}` : 'لم يتم إنشاء ملف تعلم بعد.';
      if (profile) {
        $('#nexoraDisplayName').value = profile.display_name || '';
        $('#nexoraLocale').value = profile.locale || 'ar-EG';
        $('#nexoraAdultConfirm').checked = false;
        $('#nexoraConsentConfirm').checked = false;
      }
      const [goals, paths] = await Promise.all([api('/nexora/goals'), api('/nexora/paths')]);
      renderNexoraGoals(goals.items || []); renderNexoraPaths(paths.items || []);
    } catch (e) { showToast(`تعذر تحميل مساحة NEXORA: ${e.message}`, true); }
  }
  function renderNexoraGoals(items) {
    const root=$('#nexoraGoals'); root.replaceChildren();
    if (!items.length) { const p=document.createElement('p'); p.className='empty-cell'; p.textContent='لا توجد أهداف تعلم محفوظة بعد.'; root.append(p); return; }
    for (const item of items) {
      const row=document.createElement('article'); row.className='record-row';
      const title=document.createElement('strong'); title.textContent=item.title;
      const meta=document.createElement('small'); meta.textContent=`${item.domain} · ${item.status}${item.target_date ? ` · ${item.target_date}` : ''}`;
      row.append(title,meta);
      if (item.status === 'active') {
        const button=document.createElement('button'); button.className='mini-action'; button.type='button'; button.textContent='إكمال'; button.dataset.goalId=item.id; button.dataset.goalStatus='completed'; row.append(button);
      }
      root.append(row);
    }
  }
  function renderNexoraPaths(items) {
    const root=$('#nexoraPaths'); root.replaceChildren();
    if (!items.length) { const p=document.createElement('p'); p.className='empty-cell'; p.textContent='لا توجد مسارات تعلم محفوظة بعد.'; root.append(p); return; }
    for (const item of items) {
      const row=document.createElement('article'); row.className='record-row';
      const title=document.createElement('strong'); title.textContent=item.title;
      const meta=document.createElement('small'); meta.textContent=`${item.domain} · ${item.status}`;
      const description=document.createElement('p'); description.textContent=item.objective;
      row.append(title,meta,description); root.append(row);
    }
  }
  async function saveNexoraProfile(event) {
    event.preventDefault(); const button=$('#saveNexoraProfile'); button.disabled=true;
    try {
      const payload={display_name:$('#nexoraDisplayName').value,locale:$('#nexoraLocale').value,adult_confirmed:$('#nexoraAdultConfirm').checked,consent_confirmed:$('#nexoraConsentConfirm').checked,consent_policy_version:state.nexoraConsentPolicy?.policy_version || ''};
      const result=await api('/nexora/profile',{method:'PUT',body:JSON.stringify(payload)});
      state.nexoraProfile=result.profile; $('#nexoraProfileState').textContent=`تم حفظ الملف · ${result.profile.consent_status}`;
      showToast('تم حفظ ملف التعلم في قاعدة NEXORA المستقلة.'); await loadNexoraWorkspace();
    } catch(e) { showToast(`تعذر حفظ الملف: ${e.message}`,true); }
    finally { button.disabled=false; }
  }
  async function createNexoraGoal(event) {
    event.preventDefault();
    try {
      const payload={title:$('#nexoraGoalTitle').value,domain:$('#nexoraGoalDomain').value,target_date:$('#nexoraGoalDate').value || null};
      await api('/nexora/goals',{method:'POST',body:JSON.stringify(payload)});
      $('#nexoraGoalForm').reset(); showToast('تم حفظ هدف التعلم.'); await loadNexoraWorkspace();
    } catch(e) { showToast(`تعذر إضافة الهدف: ${e.message}`,true); }
  }
  async function createNexoraPath(event) {
    event.preventDefault();
    try {
      const payload={title:$('#nexoraPathTitle').value,domain:$('#nexoraPathDomain').value,objective:$('#nexoraPathObjective').value};
      await api('/nexora/paths',{method:'POST',body:JSON.stringify(payload)});
      $('#nexoraPathForm').reset(); showToast('تم إنشاء سجل المسار في قاعدة NEXORA.'); await loadNexoraWorkspace();
    } catch(e) { showToast(`تعذر إنشاء المسار: ${e.message}`,true); }
  }
  async function revokeNexoraConsent() {
    if (!window.confirm('هل تريد سحب الموافقة؟ سيُمنع إنشاء الأهداف والمسارات وتعديل أهداف التعلم، وستظل السجلات الموجودة محفوظة حالياً.')) return;
    try { await api('/nexora/profile/revoke-consent',{method:'POST'}); showToast('تم سحب الموافقة. توقفت عمليات الكتابة الجديدة.'); await loadNexoraWorkspace(); }
    catch(e) { showToast(`تعذر سحب الموافقة: ${e.message}`,true); }
  }
  async function exportNexoraData() {
    try {
      const data = await api('/nexora/export');
      const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = `mishkat-nexora-export-${new Date().toISOString().slice(0,10)}.json`;
      document.body.append(link); link.click(); link.remove(); URL.revokeObjectURL(url);
      showToast('تم تجهيز نسخة JSON من بيانات NEXORA الخاصة بحسابك.');
    } catch(e) { showToast(`تعذر تصدير البيانات: ${e.message}`, true); }
  }

  async function updateNexoraGoal(goalId, status) {
    try { await api(`/nexora/goals/${encodeURIComponent(goalId)}?status=${encodeURIComponent(status)}`,{method:'PATCH'}); showToast('تم تحديث حالة الهدف.'); await loadNexoraWorkspace(); }
    catch(e) { showToast(`تعذر تحديث الهدف: ${e.message}`,true); }
  }

  function bindEvents() {
    document.addEventListener('click', event => {
      const viewButton=event.target.closest('[data-view]');
      if(viewButton){navigate(viewButton.dataset.view);return;}
      const action=event.target.closest('[data-action]');
      if(action?.dataset.action==='explore'){document.querySelector('#moduleGrid').scrollIntoView({behavior:'smooth',block:'center'});}
    });
    $('#localSession').addEventListener('click', startLocalSession);
    $('#checkConnections').addEventListener('click', refreshDbStatus);
    $('#refreshStatus').addEventListener('click', refreshDbStatus);
    $('#loadSources').addEventListener('click', loadSources);
    $('#nasaAction').addEventListener('click', openNasaDialog);
    $('#nasaForm').addEventListener('submit', fetchNasa);
    $('#closeNasa').addEventListener('click',()=>$('#nasaDialog').close());
    $('#cancelNasa').addEventListener('click',()=>$('#nasaDialog').close());
    $('#mobileMenu').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
    $('#refreshModuleActivity').addEventListener('click',()=>{if(state.activeModule && state.token) loadModuleActivity(state.activeModule);});
    $('#nexoraProfileForm').addEventListener('submit',saveNexoraProfile);
    $('#revokeNexoraConsent').addEventListener('click',revokeNexoraConsent);
    $('#nexoraExportData').addEventListener('click',exportNexoraData);
    $('#nexoraGoalForm').addEventListener('submit',createNexoraGoal);
    $('#nexoraPathForm').addEventListener('submit',createNexoraPath);
    $('#nexoraGoals').addEventListener('click',event=>{const button=event.target.closest('[data-goal-id]');if(button)updateNexoraGoal(button.dataset.goalId,button.dataset.goalStatus);});
  }
  function init() {
    bindEvents();
    if (state.token) $('#authStatus').textContent='رمز محلي محفوظ لهذه الجلسة';
    refreshDbStatus();
  }
  document.addEventListener('DOMContentLoaded',init);
  if ('serviceWorker' in navigator) { window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {})); }
})();
