import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import vm from 'node:vm';

// Catalogue lu directement depuis le site : aucune copie des exercices dans les tests.
const sandbox = { window: {} };
vm.runInNewContext(fs.readFileSync('exercises.js', 'utf8'), sandbox);
const exercises = sandbox.window.PYTHON_EXERCISES;

const monacoStub = String.raw`
window.require = (modules, callback) => callback();
window.require.config = () => {};
window.monaco = {
  editor: {
    create: (_, options) => {
      let value = options.value || '';
      return {
        setValue: next => { value = next; },
        getValue: () => value,
        onDidChangeModelContent: () => {}
      };
    }
  }
};`;

const supabaseStub = String.raw`
window.supabase = {
  createClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: null } }),
      signInWithPassword: async () => ({
        data: { user: { id: 'eleve-virtuel-isole' } }, error: null
      }),
      signUp: async () => ({
        data: { user: { id: 'eleve-virtuel-isole' }, session: {} }, error: null
      }),
      signOut: async () => ({ error: null })
    },
    from: () => ({
      select: () => ({
        eq: () => ({
          maybeSingle: async () => ({ data: null, error: null })
        })
      }),
      insert: async () => ({ error: null }),
      upsert: async () => ({ error: null })
    })
  })
};`;

test.beforeEach(async ({ page }) => {
  // Zéro requête vers Supabase réel ; les CDN non essentiels sont simulés.
  await page.route('**/cdn.tailwindcss.com', route =>
    route.fulfill({ status: 200, contentType: 'application/javascript', body: '' }));
  await page.route('**/loader.min.js', route =>
    route.fulfill({ status: 200, contentType: 'application/javascript', body: monacoStub }));
  await page.route('**/pyodide.js', route =>
    route.fulfill({ status: 200, contentType: 'application/javascript',
      body: 'window.loadPyodide = async () => ({ runPythonAsync: async () => {}, globals: { get: () => "" } });' }));
  await page.route('**/supabase-js@2', route =>
    route.fulfill({ status: 200, contentType: 'application/javascript', body: supabaseStub }));
  await page.route('https://*.supabase.co/**', route =>
    route.abort('blockedbyclient'));
});

async function login(page) {
  await page.goto('/eleve.html');
  await page.locator('#name').fill('Élève Virtuel Audit');
  await page.locator('#classe').selectOption({ label: '1BTS CIEL' });
  await page.locator('#studentCode').fill('7391');
  await page.locator('#enter').click();
  await expect(page.locator('#app')).toBeVisible();
  await expect(page.locator('#cloudStatus')).toContainText('Progression synchronisée');
}

test('50 exercices, mauvaise réponse, déblocage progressif et conservation locale', async ({ page }) => {
  expect(exercises).toHaveLength(50);
  await login(page);

  // Une mauvaise réponse ne valide pas Q1 et ne débloque pas la question 2.
  await page.evaluate(() => { window.execute = async () => 'UNE RÉPONSE FAUSSE'; });
  await page.locator('#test').click();
  await expect(page.locator('#tests')).toContainText('À corriger');
  await expect(page.locator('#progressText')).toHaveText('0 / 50');

  for (let i = 0; i < exercises.length; i++) {
    const ex = exercises[i];
    await expect(page.locator('#exerciseTitle')).toContainText(ex.title);

    // Simule les sorties validées. Le calcul Python réel est vérifié par
    // tests/virtual_student.py ; ici l'objectif est de tester la navigation.
    await page.evaluate(() => {
      let testIndex = 0;
      window.execute = async () => {
        const currentExercise = current();
        const tc = currentExercise.tests[testIndex++];
        if (tc.outputRegex && currentExercise.id === 'tp3q1') {
          let capital = 20000;
          const lignes = [];
          for (let an = 1; an <= 20; an++) {
            capital = Math.round(capital * 1.06);
            lignes.push('Année ' + an + ' : ' + capital + ' €');
          }
          return lignes.join('\n');
        }
        return (tc.expected ?? '1').trim();
      };
    });
    await page.locator('#test').click();
    await expect(page.locator('#stateBadge')).toHaveText('✅ Validé');
    await expect(page.locator('#progressText')).toHaveText(`${i + 1} / 50`);

    if (i + 1 < exercises.length) {
      await expect(page.locator('#exerciseTitle')).toContainText(exercises[i + 1].title);
    }

    if (i === 4) {
      // Le TP2 est maintenant accessible, même après actualisation de la page.
      await page.reload();
      await page.locator('#name').fill('Élève Virtuel Audit');
      await page.locator('#classe').selectOption({ label: '1BTS CIEL' });
      await page.locator('#studentCode').fill('7391');
      await page.locator('#enter').click();
      await expect(page.locator('#progressText')).toHaveText('5 / 50');
      await expect(page.locator('#exerciseTitle')).toContainText(exercises[5].title);
    }
  }

  await expect(page.locator('#progressText')).toHaveText('50 / 50');
  await expect(page.locator('#stateBadge')).toHaveText('✅ Validé');
});

test('l’accueil ne montre plus l’ancienne interface', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/eleve\.html/);
  await expect(page.locator('#classe')).toBeVisible();
  await expect(page.locator('#name')).toBeVisible();
});
