// Synchronisation Supabase pour Python Submit (GitHub Pages)
// La clé publishable est publique par conception. La sécurité repose sur Supabase Auth + RLS.
(() => {
  const SUPABASE_URL = 'https://hxfdlujpedxuumqfewvn.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_RMv9HFpnXdId5VxUVy_sDg_Kq57S_lF';
  let sb = null;
  let authUser = null;
  let syncing = false;

  function slug(s) {
    return (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/[^a-z0-9]+/g, '.').replace(/^\.|\.$/g, '');
  }
  function syntheticEmail(name, classe) {
    return `${slug(name)}.${slug(classe)}@python-submit.local`;
  }
  function codeToPassword(code) {
    // Supabase impose généralement >= 6 caractères pour un mot de passe.
    return `Ps!${code}`;
  }
  function setSyncStatus(text, ok=true) {
    const el = document.getElementById('cloudStatus');
    if (el) { el.textContent = text; el.className = `text-xs ${ok?'text-green-600':'text-amber-600'}`; }
  }

  async function loadSdk() {
    if (sb) return sb;
    await new Promise((resolve, reject) => {
      if (window.supabase) return resolve();
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      s.onload = resolve; s.onerror = reject; document.head.appendChild(s);
    });
    sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    return sb;
  }

  async function authenticate(name, classe, code) {
    await loadSdk();
    const email = syntheticEmail(name, classe);
    const password = codeToPassword(code);
    let { data, error } = await sb.auth.signInWithPassword({ email, password });
    if (error) {
      const signup = await sb.auth.signUp({ email, password, options:{ data:{ student_name:name, class_name:classe } } });
      if (signup.error) throw signup.error;
      data = signup.data;
      if (!data.session) throw new Error("Compte créé mais confirmation requise. Désactive 'Confirm email' dans Supabase Auth pour les comptes élèves.");
    }
    authUser = data.user;
    localStorage.setItem('ps_student_code', code);
    return authUser;
  }

  async function loadCloudProgress(name, classe) {
    if (!authUser) return;
    const { data, error } = await sb.from('student_progress')
      .select('robpy_progress,completed_exercises').eq('user_id', authUser.id).maybeSingle();
    if (error) throw error;
    if (!data) {
      const localDone = JSON.parse(localStorage.getItem(`python_submit_done_${name}_${classe}`)||'[]');
      const localRob = JSON.parse(localStorage.getItem(`robpy_${name}`)||'[]');
      const ins = await sb.from('student_progress').insert({
        user_id:authUser.id, student_name:name, class_name:classe,
        robpy_progress:Math.min(localRob.length,10), completed_exercises:localDone
      });
      if (ins.error) throw ins.error;
    } else {
      const localDone = JSON.parse(localStorage.getItem(`python_submit_done_${name}_${classe}`)||'[]');
      const mergedDone = [...new Set([...(data.completed_exercises||[]), ...localDone])];
      localStorage.setItem(`python_submit_done_${name}_${classe}`, JSON.stringify(mergedDone));
      const localRob = JSON.parse(localStorage.getItem(`robpy_${name}`)||'[]');
      const n = Math.max(Number(data.robpy_progress)||0, localRob.length);
      localStorage.setItem(`robpy_${name}`, JSON.stringify(Array.from({length:Math.min(n,10)},(_,i)=>i)));
      await saveCloudProgress(name, classe);
    }
    setSyncStatus('☁️ Progression synchronisée');
  }

  async function saveCloudProgress(name, classe) {
    if (!authUser || syncing) return;
    syncing = true;
    try {
      const completed = JSON.parse(localStorage.getItem(`python_submit_done_${name}_${classe}`)||'[]');
      const robpy = JSON.parse(localStorage.getItem(`robpy_${name}`)||'[]');
      const { error } = await sb.from('student_progress').upsert({
        user_id:authUser.id, student_name:name, class_name:classe,
        robpy_progress:Math.min(robpy.length,10), completed_exercises:completed
      }, { onConflict:'user_id' });
      if (error) throw error;
      setSyncStatus('☁️ Sauvegardé');
    } catch(e) { console.error(e); setSyncStatus('☁️ Hors ligne — sauvegarde locale conservée', false); }
    finally { syncing=false; }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const classe = document.getElementById('classe');
    const enter = document.getElementById('enter');
    const name = document.getElementById('name');
    if (!classe || !enter || !name) return;

    const code = document.createElement('input');
    code.id='studentCode'; code.type='password'; code.inputMode='numeric'; code.autocomplete='current-password';
    code.placeholder='Code personnel (4 chiffres)'; code.maxLength=4;
    code.className='w-full border rounded-lg px-3 py-2';
    classe.insertAdjacentElement('afterend', code);
    const cloud = document.createElement('p'); cloud.id='cloudStatus'; cloud.className='text-xs text-gray-500';
    cloud.textContent='☁️ La progression sera synchronisée avec Supabase';
    code.insertAdjacentElement('afterend', cloud);
    code.value = localStorage.getItem('ps_student_code') || '';

    enter.addEventListener('click', async (ev) => {
      if (enter.dataset.authenticated==='1') { enter.dataset.authenticated='0'; return; }
      ev.preventDefault(); ev.stopImmediatePropagation();
      const n=name.value.trim(), c=classe.value, pin=code.value.trim();
      const err=document.getElementById('loginerr');
      if(!n||!c||!/^[0-9]{4}$/.test(pin)) {
        if(err){err.textContent='Renseignez votre nom, votre classe et un code personnel de 4 chiffres.';err.classList.remove('hidden');}
        return;
      }
      enter.disabled=true; enter.textContent='Connexion…';
      try {
        await authenticate(n,c,pin);
        await loadCloudProgress(n,c);
        enter.dataset.authenticated='1';
        enter.disabled=false; enter.textContent='Accéder';
        enter.click();
      } catch(e) {
        console.error(e); if(err){err.textContent='Connexion impossible : '+e.message;err.classList.remove('hidden');}
        enter.disabled=false; enter.textContent='Accéder';
      }
    }, true);

    // Synchronise automatiquement toute validation locale TP/ROBPY.
    const originalSet = localStorage.setItem.bind(localStorage);
    localStorage.setItem = function(k,v){
      originalSet(k,v);
      const n=name.value.trim() || localStorage.getItem('ps_name') || '';
      const c=classe.value || localStorage.getItem('ps_class') || '';
      if(authUser && (k===`python_submit_done_${n}_${c}` || k===`robpy_${n}`)) setTimeout(()=>saveCloudProgress(n,c),50);
    };
  });

  window.PythonSubmitCloud = { save: saveCloudProgress };
})();