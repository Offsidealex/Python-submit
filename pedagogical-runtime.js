/* Correcteur pédagogique : utilise l'AST Python de Pyodide, jamais une
   recherche de mots dans le texte. Ne modifie ni progression ni Supabase. */
(() => {
  let rulesReady = null;
  let activeRuntime = null;

  async function loadRules(runtime) {
    if (runtime !== activeRuntime) {
      activeRuntime = runtime;
      rulesReady = null;
    }
    if (!rulesReady) {
      rulesReady = fetch('pedagogical_checks.py?v=3')
        .then(async response => {
          if (!response.ok) throw new Error('Règles de vérification indisponibles (' + response.status + ')');
          return response.text();
        })
        .then(source => runtime.runPythonAsync(source))
        .catch(error => {
          rulesReady = null; // permet de réessayer sans recharger la page
          throw error;
        });
    }
    return rulesReady;
  }

  async function inspect(runtime, exerciseId, program) {
    if (!runtime) throw new Error('Python est encore en cours de chargement.');
    await loadRules(runtime);
    const code = 'import json\n_ps_validate_result=json.dumps(validate_code('
      + JSON.stringify(exerciseId) + ', ' + JSON.stringify(program)
      + '), ensure_ascii=False)';
    await runtime.runPythonAsync(code);
    const raw = runtime.globals.get('_ps_validate_result');
    return JSON.parse(String(raw));
  }

  function diceProgram(program, rolls) {
    if (!Array.isArray(rolls) || !rolls.length
        || !rolls.every(x => Number.isInteger(x) && x >= 1 && x <= 6)) {
      throw new Error('Scénario de dés incorrect.');
    }
    // On remplace temporairement random.randint(1,6), puis on le restaure,
    // même si le programme élève déclenche une erreur.
    return [
      'import random as _ps_random',
      '_ps_original_randint=_ps_random.randint',
      '_ps_rolls=iter(' + JSON.stringify(rolls) + ')',
      'def _ps_controlled_randint(a,b):',
      '    if (a,b)!=(1,6):',
      '        raise ValueError("Utiliser random.randint(1,6) pour chaque dé.")',
      '    try:',
      '        return next(_ps_rolls)',
      '    except StopIteration:',
      '        raise RuntimeError("Trop de lancers de dés ou boucle incorrecte.")',
      '_ps_random.randint=_ps_controlled_randint',
      'try:',
      '    exec(' + JSON.stringify(program) + ', {"__name__":"__main__"})',
      'finally:',
      '    _ps_random.randint=_ps_original_randint',
    ].join('\n');
  }

  window.PythonPedagogical = {inspect, diceProgram};
})();
