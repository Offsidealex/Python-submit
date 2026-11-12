# Élève virtuel — Python Submit

Ce dossier contient un contrôle automatique **sans accès aux comptes réels**.

## Couverture

- `virtual_student.py` : lit `exercises.js`, exécute une solution de référence pour chaque exercice, vérifie les sorties pour tous les jeux d'entrées, puis vérifie qu'une mauvaise réponse est rejetée. Les fichiers temporaires de TP8 et TP10 restent dans un répertoire isolé. Un rapport `rapport-exercices.md` est généré.
- `parcours-eleve.spec.mjs` : ouvre l'interface dans Chromium via Playwright, simule une authentification Supabase en mémoire, vérifie le refus d'une mauvaise réponse, parcourt les 50 exercices, le déblocage d'un TP au suivant, la progression et sa conservation après actualisation.
- `../.github/workflows/eleve-virtuel.yml` : exécute les deux séries automatiquement sur `github-pages-eleves` et produit deux artefacts de rapport.

Le navigateur utilise un **simulateur de correction** pour tester les boutons et la navigation ; la validité effective des programmes Python est vérifiée séparément dans `virtual_student.py`. Il ne contacte **jamais** le projet Supabase réel : les tests de synchronisation sur deux ordinateurs devront se faire avec un compte de test distinct, manuellement ou dans un environnement de staging.

## Lancer en local

Nécessite Python 3 et Node.js.

```bash
python3 tests/virtual_student.py
npm install
npx playwright install chromium
npm run test:browser
```

Pour consulter l'historique, ouvrir **GitHub > Actions > Élève virtuel — Python Submit** ; télécharger `rapport-50-exercices` et `rapport-parcours-navigateur` depuis l'exécution souhaitée.

Les scripts ne changent ni le code d'un élève ni les lignes de la base. Ne jamais y introduire des identifiants Supabase réels.
