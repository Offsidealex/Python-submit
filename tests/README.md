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

## Audit pédagogique V2

Le script `audit_pedagogique.py` lance **plus de 300 scénarios**, couvrant les 50 exercices :
solution de référence, variante syntaxique, sortie fausse, erreur Python, réponse codée en dur, méthodes alternatives pour TP1 à TP3, valeurs limites et vérification réelle des fichiers du TP8/TP10.

Exécution locale :

```bash
python3 tests/audit_pedagogique.py
```

Deux rapports sont créés dans le dossier `tests/` :

- `rapport-pedagogique.md` : bilan par TP et anomalies détaillées.
- `rapport-pedagogique.json` : données structurées des scénarios.

Les statuts **RISQUE**, **MANQUE** et **ALERTE** sont des résultats d'audit, pas des validations. Le workflow échoue en cas de **régression** du programme correct ou si le nombre de scénarios descend sous 250 ; une alerte pédagogique n'est pas volontairement traitée comme un échec technique.

### Corrections déjà apportées au catalogue
- TP1 Q3 : plusieurs couples de résistance/intensité, afin de détecter les réponses figées.
- TP2 Q1, Q2 et Q5 : vérification des seuils exacts.
- TP3 Q1 : contrôle des 20 montants, en tolérant deux conventions usuelles d'arrondi.
- TP8 Q1 à Q5 et TP10 Q4 : la validation vérifie maintenant **l'existence et le contenu du fichier créé** dans la mémoire de Pyodide, au lieu de contrôler seulement le texte imprimé.

### Limites de l'automatisation
Une sortie correcte ne garantit pas toujours la qualité de l'algorithme (fonction demandée, boucle effective, dé, lecture réelle de fichier). Certaines exigences doivent être évaluées par des scénarios d'exécution supplémentaires ou par une analyse Python AST. Le navigateur Playwright simule les calculs et le cloud ; il ne remplace pas une évaluation pédagogique humaine ni un test réel de synchronisation Supabase.
