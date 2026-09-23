// Synchronisation Supabase pour Python Submit (GitHub Pages)
// La clé publishable est publique par conception. La sécurité repose sur Supabase Auth + RLS.
(() => {
  const SUPABASE_URL='https://hxfdlujpedxuumqfewvn.supabase.co';
  const SUPABASE_KEY='sb_publishable_RMv9HFpnXdId5VxUVy_sDg_Kq57S_lF';
  let sb=null,authUser=null,syncing=false,authInFlight=false;
  const slug=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'.').replace(/^\.|\.$/g,'');
  const syntheticEmail=(name,classe)=>`${slug(name)}.${slug(classe)}@python-submit.local`;
  const codeToPassword=code=>`Ps!${code}`;
  function isRateLimit(e){const m=(e?.message||'').toLowerCase();return e?.status===429||m.includes('rate limit')||m.includes('too many requests')}
  function friendlyError(e){if(isRateLimit(e))return 'Trop de tentatives de connexion. Attends quelques minutes avant de réessayer.';return e?.message||'Erreur inconnue.'}
  function setSyncStatus(text,ok=true){const el=document.getElementById('loginCloudStatus')||document.getElementById('cloudStatus');if(el){el.textContent=text;el.className=`text-xs ${ok?'text-green-600':'text-amber-600'}`}}
  async function loadSdk(){if(sb)return sb;await new Promise((resolve,reject)=>{if(window.supabase)return resolve();const s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';s.onload=resolve;s.onerror=reject;document.head.appendChild(s)});sb=window.supabase.createClient(SUPABASE_URL,SUPABASE_KEY);return sb}
  async function authenticate(name,classe,code){
    await loadSdk();
    // Si ce navigateur possède déjà une session valide pour le même compte, aucun nouvel appel de login.
    const email=syntheticEmail(name,classe),password=codeToPassword(code);
    const session=await sb.auth.getSession();
    if(session.data?.session?.user?.email===email){authUser=session.data.session.user;localStorage.setItem('ps_student_code',code);return authUser}
    let {data,error}=await sb.auth.signInWithPassword({email,password});
    if(error){
      if(isRateLimit(error))throw error;
      const msg=(error.message||'').toLowerCase();
      if(msg.includes('invalid login')||msg.includes('invalid credentials')){
        // Une seule tentative d'inscription. Aucun retry automatique derrière.
        const signup=await sb.auth.signUp({email,password,options:{data:{student_name:name,class_name:classe}}});
        if(signup.error){
          if(isRateLimit(signup.error))throw signup.error;
          if((signup.error.message||'').toLowerCase().includes('already registered'))throw new Error('Ce compte existe déjà : le code personnel saisi n’est pas le bon.');
          throw signup.error;
        }
        data=signup.data;
        if(!data.session)throw new Error('Compte créé mais confirmation requise.');
      }else throw error;
    }
    authUser=data.user;localStorage.setItem('ps_student_code',code);return authUser;
  }
  async function loadCloudProgress(name,classe){if(!authUser)return;const {data,error}=await sb.from('student_progress').select('robpy_progress,completed_exercises').eq('user_id',authUser.id).maybeSingle();if(error)throw error;if(!data){let localDone=[],localRob=[];try{localDone=JSON.parse(localStorage.getItem(`python_submit_done_${name}_${classe}`)||'[]');localRob=JSON.parse(localStorage.getItem(`robpy_${name}`)||'[]')}catch{}const ins=await sb.from('student_progress').insert({user_id:authUser.id,student_name:name,class_name:classe,robpy_progress:Math.min(localRob.length,10),completed_exercises:localDone});if(ins.error)throw ins.error}else{let localDone=[],localRob=[];try{localDone=JSON.parse(localStorage.getItem(`python_submit_done_${name}_${classe}`)||'[]');localRob=JSON.parse(localStorage.getItem(`robpy_${name}`)||'[]')}catch{}localStorage.setItem(`python_submit_done_${name}_${classe}`,JSON.stringify([...new Set([...(data.completed_exercises||[]),...localDone])]));const n=Math.max(Number(data.robpy_progress)||0,localRob.length);localStorage.setItem(`robpy_${name}`,JSON.stringify(Array.from({length:Math.min(n,10)},(_,i)=>i)));await saveCloudProgress(name,classe)}setSyncStatus('☁️ Progression synchronisée')}
  async function saveCloudProgress(name,classe){if(!authUser||syncing)return;syncing=true;try{let completed=[],robpy=[];try{completed=JSON.parse(localStorage.getItem(`python_submit_done_${name}_${classe}`)||'[]');robpy=JSON.parse(localStorage.getItem(`robpy_${name}`)||'[]')}catch{}const {error}=await sb.from('student_progress').upsert({user_id:authUser.id,student_name:name,class_name:classe,robpy_progress:Math.min(robpy.length,10),completed_exercises:completed},{onConflict:'user_id'});if(error)throw error;setSyncStatus('☁️ Sauvegardé')}catch(e){console.error(e);setSyncStatus('☁️ Hors ligne — sauvegarde locale conservée',false)}finally{syncing=false}}
  document.addEventListener('DOMContentLoaded',()=>{const classe=document.getElementById('classe'),enter=document.getElementById('enter'),name=document.getElementById('name');if(!classe||!enter||!name)return;
    document.querySelectorAll('#studentCode').forEach((el,i)=>{if(i>0)el.remove()});
    let code=document.getElementById('studentCode');if(!code){code=document.createElement('input');code.id='studentCode';code.type='password';code.inputMode='numeric';code.autocomplete='current-password';code.placeholder='Code personnel (4 chiffres)';code.maxLength=4;code.className='w-full border rounded-lg px-3 py-2';classe.insertAdjacentElement('afterend',code)}
    let cloud=document.getElementById('loginCloudStatus');if(!cloud){cloud=document.createElement('p');cloud.id='loginCloudStatus';cloud.className='text-xs text-gray-500';cloud.textContent='☁️ La progression sera synchronisée avec Supabase';code.insertAdjacentElement('afterend',cloud)}code.value=localStorage.getItem('ps_student_code')||'';
    enter.addEventListener('click',async ev=>{
      if(enter.dataset.authenticated==='1'){enter.dataset.authenticated='0';return}
      ev.preventDefault();ev.stopImmediatePropagation();
      if(authInFlight)return;
      const n=name.value.trim(),c=classe.value,pin=code.value.trim(),err=document.getElementById('loginerr');
      if(!n||!c||!/^[0-9]{4}$/.test(pin)){if(err){err.textContent='Renseignez votre nom, votre classe et un code personnel de 4 chiffres.';err.classList.remove('hidden')}return}
      if(err)err.classList.add('hidden');authInFlight=true;enter.disabled=true;enter.textContent='Connexion…';
      try{await authenticate(n,c,pin);await loadCloudProgress(n,c);enter.dataset.authenticated='1';enter.disabled=false;enter.textContent='Accéder';authInFlight=false;enter.click()}
      catch(e){console.error(e);if(err){err.textContent=friendlyError(e);err.classList.remove('hidden')}if(isRateLimit(e))setSyncStatus('☁️ Supabase limite temporairement les connexions — aucune progression locale n’est perdue.',false);enter.disabled=false;enter.textContent='Accéder';authInFlight=false}
    },true);
    const originalSet=localStorage.setItem.bind(localStorage);localStorage.setItem=function(k,v){originalSet(k,v);const n=name.value.trim()||localStorage.getItem('ps_name')||'',c=classe.value||localStorage.getItem('ps_class')||'';if(authUser&&(k===`python_submit_done_${n}_${c}`||k===`robpy_${n}`))setTimeout(()=>saveCloudProgress(n,c),50)};
  });
  window.PythonSubmitCloud={save:saveCloudProgress,signOut:async()=>{if(!sb)await loadSdk();return sb.auth.signOut()}};
})();