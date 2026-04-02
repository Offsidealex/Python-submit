# Python Submit

Plateforme de dépôt et de correction automatique d'exercices Python pour les élèves de BTS au **Lycée Denis Diderot – Belfort**.

🌐 **Interface élève** : [offsidealex.github.io/Python-submit](https://offsidealex.github.io/Python-submit/)

---

## Fonctionnalités

### Côté élève (`index.html`)
- Connexion par nom et classe
- Éditeur de code Monaco (coloration syntaxique, autocomplétion)
- Exécution Python dans le navigateur via **Pyodide** (sans serveur)
- Support de `input()` avec collecteur de valeurs intégré
- Tests automatiques avant soumission
- Soumission du code avec affichage immédiat de la **note et du commentaire IA**
- Sauvegarde automatique du brouillon par question (localStorage)
- Tutoriel gamifié **ROBPY** (`tuto.html`) — 10 niveaux progressifs

### Côté professeur (`prof.html`)
- Dashboard protégé par mot de passe
- Visualisation de toutes les soumissions par classe et par TP
- Note et commentaire générés automatiquement par **Claude Haiku (IA)**
- Suppression de soumission individuelle
- Bouton actualiser sans rechargement de page

### Anti-triche
- Détection de changement d'onglet / fenêtre (`visibilitychange` + `blur`)
- 1er écart : avertissement –1 point
- 2e écart : soumission automatique avec note 0
- Événements enregistrés côté serveur (résistant aux DevTools)
- Mode test enseignant : `?mode=test` dans l'URL désactive l'anti-triche

---

## Structure des exercices

| TP | Thème | Questions |
|----|-------|-----------|
| TP1 | Variables, types, f-string (loi d'Ohm) | Q1–Q5 |
| TP2 | Structures conditionnelles (LED, régulateur…) | Q1–Q5 |
| TP3 | Boucles for/while | Q1–Q5 |

- Notation : **2 points par question**
- Correction automatique par IA (Claude Haiku)
- Ordre d'affichage alphabétique

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | HTML / Tailwind CSS / JavaScript |
| Éditeur | Monaco Editor |
| Exécution Python | Pyodide (WASM) |
| Backend API | FastAPI + Python |
| Base de données | PostgreSQL |
| Hébergement frontend | GitHub Pages |
| Hébergement backend | Render |
| Correction IA | Anthropic Claude Haiku |

---

## Installation locale (backend)

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Variables d'environnement requises :
```
DATABASE_URL=postgresql://...
TEACHER_PASSWORD=...
ANTHROPIC_API_KEY=...
```

---

## Déploiement

- **Frontend** : push sur `main` → GitHub Pages met à jour automatiquement
- **Backend** : déployé sur Render via `render.yaml`
