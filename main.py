from fastapi import FastAPI, HTTPException, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
import psycopg2.extras
import json
import os
import random
import string
import anthropic

app = FastAPI(title="Python Submit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "diderot2024")
DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            deadline TEXT,
            test_cases TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS class_codes (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            class_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id SERIAL PRIMARY KEY,
            student_name TEXT NOT NULL,
            class_id TEXT NOT NULL,
            exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            output TEXT DEFAULT '',
            test_results TEXT DEFAULT '[]',
            grade NUMERIC,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migrations
    try:
        cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS grade NUMERIC")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS ai_comment TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS tab_switches INTEGER DEFAULT 0")
    except Exception:
        pass
    # Mise à jour TP3-Q4 : remplacer la devinette (input) par lancer de dés
    try:
        cur.execute(
            "UPDATE exercises SET description=%s WHERE title='TP3 - Q4'",
            (
                "Simuler un jeu de dés avec une boucle while.\n"
                "À chaque tour, lancer deux dés (utiliser random.randint(1, 6)) et afficher les valeurs obtenues.\n"
                "S'arrêter dès qu'un double est obtenu (les deux dés ont la même valeur).\n"
                "Afficher le nombre de lancers nécessaires.\n\n"
                "Exemple de sortie :\n"
                "Lancer 1 : dé1=3, dé2=5\n"
                "Lancer 2 : dé1=2, dé2=6\n"
                "Lancer 3 : dé1=4, dé2=4 → DOUBLE !\n"
                "Double obtenu en 3 lancers.",
            )
        )
    except Exception:
        pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cheat_events (
            id SERIAL PRIMARY KEY,
            student_name TEXT NOT NULL,
            class_id TEXT NOT NULL,
            exercise_id INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (student_name, class_id, exercise_id)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def seed_exercises():
    exercises = [
        # ── TP1 : Variables et types de données (contexte : loi d'Ohm) ──
        {
            "title": "TP1 - Q1",
            "description": (
                "Contexte : loi d'Ohm — U = R × I\n\n"
                "Déclarer R = 470 et I = 0.02, calculer la tension U = R * I et l'afficher.\n"
                "Vérifier que U = 9.4 V.\n\n"
                "Exemple de sortie attendue :\n"
                "Tension U = 9.4 V"
            ),
        },
        {
            "title": "TP1 - Q2",
            "description": (
                "Utiliser type() pour afficher le type de R, I et d'une variable nom = \"Résistance\".\n\n"
                "Exemple de sortie attendue :\n"
                "<class 'int'>\n"
                "<class 'float'>\n"
                "<class 'str'>"
            ),
        },
        {
            "title": "TP1 - Q3",
            "description": (
                "Demander R et I à l'utilisateur avec input(), les convertir en float().\n"
                "Recalculer et afficher U = R * I.\n\n"
                "Entrées à fournir (dans l'ordre) : valeur de R, valeur de I.\n\n"
                "Exemple avec R=470 et I=0.02 :\n"
                "Tension U = 9.4 V"
            ),
        },
        {
            "title": "TP1 - Q4",
            "description": (
                "Avec R = 470 et I = 0.02, calculer la puissance P = U * I (où U = R * I).\n"
                "Afficher P arrondi à 4 décimales avec round() et l'unité watts.\n\n"
                "Exemple de sortie attendue :\n"
                "Puissance P = 0.1881 watts"
            ),
        },
        {
            "title": "TP1 - Q5",
            "description": (
                "Avec R = 470, I = 0.02, U = R * I et P = U * I, afficher un résumé complet avec une f-string :\n\n"
                "Exemple de sortie attendue :\n"
                "R = 470 Ω | I = 0.02 A | U = 9.4 V | P = 0.188 W"
            ),
        },
        # ── TP2 : Structures conditionnelles (contexte : seuils de tension) ──
        {
            "title": "TP2 - Q1",
            "description": (
                "Contexte : seuils de tension dans un circuit électronique\n\n"
                "Une LED est passante si U > 2.0 V.\n"
                "Demander U à l'utilisateur et afficher \"LED allumée\" ou \"LED éteinte\".\n\n"
                "Entrée à fournir : valeur de U en volts.\n\n"
                "Exemple avec U=3.0 :\n"
                "LED allumée\n\n"
                "Exemple avec U=1.5 :\n"
                "LED éteinte"
            ),
        },
        {
            "title": "TP2 - Q2",
            "description": (
                "Classifier la tension de sortie d'un régulateur en 3 zones avec if/elif/else :\n"
                "- faible si U < 4.5 V\n"
                "- nominale si 4.5 <= U <= 5.5 V\n"
                "- élevée si U > 5.5 V\n\n"
                "Demander U à l'utilisateur.\n\n"
                "Entrée à fournir : valeur de U en volts.\n\n"
                "Exemple avec U=5.0 :\n"
                "Tension nominale\n\n"
                "Exemple avec U=6.0 :\n"
                "Tension élevée"
            ),
        },
        {
            "title": "TP2 - Q3",
            "description": (
                "Un système se déclenche si U > 12 V ET I > 2 A (utiliser and).\n"
                "Tester 3 combinaisons en déclarant les valeurs directement dans le code (pas d'input) :\n"
                "- U=15, I=3 → déclenchement\n"
                "- U=10, I=3 → pas de déclenchement\n"
                "- U=15, I=1 → pas de déclenchement\n\n"
                "Exemple de sortie attendue :\n"
                "U=15 I=3 : Système déclenché\n"
                "U=10 I=3 : Système non déclenché\n"
                "U=15 I=1 : Système non déclenché"
            ),
        },
        {
            "title": "TP2 - Q4",
            "description": (
                "Afficher la table de vérité d'une porte AND pour A, B dans {0, 1} "
                "avec deux boucles for imbriquées.\n\n"
                "Exemple de sortie attendue :\n"
                "A=0 B=0 : 0\n"
                "A=0 B=1 : 0\n"
                "A=1 B=0 : 0\n"
                "A=1 B=1 : 1"
            ),
        },
        {
            "title": "TP2 - Q5",
            "description": (
                "Un thermostat :\n"
                "- coupe le chauffage si T > 22°C → afficher \"Chauffage coupé\"\n"
                "- allume le chauffage si T < 18°C → afficher \"Chauffage allumé\"\n"
                "- affiche \"Maintien\" sinon\n\n"
                "Demander T à l'utilisateur.\n\n"
                "Entrée à fournir : valeur de T en °C.\n\n"
                "Exemple avec T=25 :\n"
                "Chauffage coupé\n\n"
                "Exemple avec T=20 :\n"
                "Maintien"
            ),
        },
        # ── TP3 : Boucles for et while ──
        {
            "title": "TP3 - Q1",
            "description": (
                "Un capital de 20 000 € est placé à un taux annuel de 6 %.\n"
                "Avec une boucle for, afficher le capital à la fin de chacune des 20 premières années, arrondi à l'unité.\n\n"
                "Aide : utiliser la fonction round().\n\n"
                "Exemple de sortie attendue :\n"
                "Année 1 : 21200 €\n"
                "Année 2 : 22472 €\n"
                "..."
            ),
        },
        {
            "title": "TP3 - Q2",
            "description": (
                "Avec une boucle while, diviser U = 100 V par 2 à chaque tour jusqu'à ce que U < 1 V.\n"
                "Afficher le nombre d'itérations nécessaires."
            ),
        },
        {
            "title": "TP3 - Q3",
            "description": (
                "Avec une boucle for, calculer la somme 1 + 2 + 3 + ... + 200.\n"
                "Vérifier le résultat avec la formule n*(n+1)//2 et afficher les deux valeurs."
            ),
        },
        {
            "title": "TP3 - Q4",
            "description": (
                "Simuler un jeu de dés avec une boucle while.\n"
                "À chaque tour, lancer deux dés (utiliser random.randint(1, 6)) et afficher les valeurs obtenues.\n"
                "S'arrêter dès qu'un double est obtenu (les deux dés ont la même valeur).\n"
                "Afficher le nombre de lancers nécessaires.\n\n"
                "Exemple de sortie :\n"
                "Lancer 1 : dé1=3, dé2=5\n"
                "Lancer 2 : dé1=2, dé2=6\n"
                "Lancer 3 : dé1=4, dé2=4 → DOUBLE !\n"
                "Double obtenu en 3 lancers."
            ),
        },
        {
            "title": "TP3 - Q5",
            "description": (
                "Afficher une table de multiplication de 1 à 5 avec deux boucles for imbriquées.\n"
                "Aligner les colonnes avec le format :>4d.\n\n"
                "Exemple de sortie :\n"
                "   1   2   3   4   5\n"
                "   2   4   6   8  10\n"
                "..."
            ),
        },
        # ── TP4 : Fonctions ──
        {
            "title": "TP4 - Q1",
            "description": (
                "Écrire une fonction loi_ohm(R, I) qui retourne la tension U = R * I.\n"
                "Appeler la fonction avec R = 470 Ω et I = 0.02 A puis afficher le résultat.\n\n"
                "Sortie attendue :\nU = 9.4 V"
            ),
        },
        {
            "title": "TP4 - Q2",
            "description": (
                "Écrire une fonction puissance(U, I) qui retourne P = U * I.\n"
                "Tester avec U = 12 V et I = 1.5 A puis afficher P.\n\n"
                "Sortie attendue :\nP = 18.0 W"
            ),
        },
        {
            "title": "TP4 - Q3",
            "description": (
                "Écrire une fonction diviseur(Ue, R1, R2) qui retourne la tension de sortie "
                "Us = Ue * R2 / (R1 + R2).\n"
                "Tester avec Ue=12, R1=1000 et R2=2000.\n\n"
                "Sortie attendue :\nUs = 8.0 V"
            ),
        },
        {
            "title": "TP4 - Q4",
            "description": (
                "Écrire une fonction resistance_led(Ualim, Uled=2.0, I=0.02) qui retourne "
                "la résistance R = (Ualim - Uled) / I.\n"
                "Utiliser les valeurs par défaut avec Ualim=5 puis afficher R.\n\n"
                "Sortie attendue :\nR = 150.0 ohms"
            ),
        },
        {
            "title": "TP4 - Q5",
            "description": (
                "Écrire une fonction mesures(R, I) qui retourne trois valeurs : U, P et E, "
                "avec U=R*I, P=U*I et E=P*3600 (énergie consommée en une heure).\n"
                "Tester avec R=100 et I=0.1 et afficher les trois résultats."
            ),
        },

        # ── TP5 : Listes et séries de mesures ──
        {
            "title": "TP5 - Q1",
            "description": (
                "Créer la liste mesures = [4.98, 5.02, 4.95, 5.10, 4.88].\n"
                "Afficher la première mesure, la dernière mesure et le nombre de mesures."
            ),
        },
        {
            "title": "TP5 - Q2",
            "description": (
                "Reprendre la liste mesures. Ajouter 5.05 avec append(), puis afficher la liste complète "
                "et sa nouvelle longueur."
            ),
        },
        {
            "title": "TP5 - Q3",
            "description": (
                "Avec mesures = [4.98, 5.02, 4.95, 5.10, 4.88], afficher la valeur minimale, "
                "la valeur maximale et la moyenne arrondie à 3 décimales."
            ),
        },
        {
            "title": "TP5 - Q4",
            "description": (
                "Parcourir mesures = [4.98, 5.02, 4.95, 5.10, 4.88] avec une boucle for.\n"
                "Afficher uniquement les mesures strictement inférieures à 5.0 V."
            ),
        },
        {
            "title": "TP5 - Q5",
            "description": (
                "À partir de mesures = [4.98, 5.02, 4.95, 5.10, 4.88], créer une nouvelle liste "
                "contenant les écarts absolus à 5.0 V. Afficher cette liste puis l'écart maximal."
            ),
        },

        # ── TP6 : Chaînes et trames série ──
        {
            "title": "TP6 - Q1",
            "description": (
                "On reçoit la trame texte \"START:12.5:STOP\".\n"
                "Découper la trame avec split(':') et afficher les trois éléments obtenus."
            ),
        },
        {
            "title": "TP6 - Q2",
            "description": (
                "Avec trame = \"START:12.5:STOP\", extraire la valeur 12.5, la convertir en float "
                "et afficher : Valeur = 12.5 V."
            ),
        },
        {
            "title": "TP6 - Q3",
            "description": (
                "Demander une trame à l'utilisateur. Vérifier avec startswith() qu'elle commence par "
                "\"START\" et afficher \"Trame valide\" ou \"Trame invalide\"."
            ),
        },
        {
            "title": "TP6 - Q4",
            "description": (
                "Nettoyer la chaîne \"  temp:23.7  \" avec strip(), la convertir en majuscules "
                "puis afficher le résultat."
            ),
        },
        {
            "title": "TP6 - Q5",
            "description": (
                "Analyser la trame \"CAPTEUR:TEMP:23.7:C\" avec split(':').\n"
                "Afficher avec une f-string : Capteur TEMP : 23.7 C."
            ),
        },

        # ── TP7 : Dictionnaires et composants ──
        {
            "title": "TP7 - Q1",
            "description": (
                "Créer le dictionnaire composant = {'reference':'R470', 'valeur':470, 'tolerance':5}.\n"
                "Afficher séparément la référence, la valeur et la tolérance."
            ),
        },
        {
            "title": "TP7 - Q2",
            "description": (
                "Modifier la tolérance du composant R470 de 5 à 1 %, puis ajouter la clé "
                "'puissance' avec la valeur 0.25. Afficher le dictionnaire."
            ),
        },
        {
            "title": "TP7 - Q3",
            "description": (
                "Parcourir un dictionnaire de composant avec items() et afficher chaque clé et sa valeur "
                "sous la forme : cle = valeur."
            ),
        },
        {
            "title": "TP7 - Q4",
            "description": (
                "Créer un catalogue contenant R470 (470 Ω), R1K (1000 Ω) et R2K2 (2200 Ω).\n"
                "Demander une référence à l'utilisateur et afficher sa valeur si elle existe, "
                "sinon afficher \"Référence inconnue\"."
            ),
        },
        {
            "title": "TP7 - Q5",
            "description": (
                "Créer un dictionnaire imbriqué pour trois capteurs avec leur type et leur valeur.\n"
                "Parcourir le dictionnaire et afficher pour chaque capteur son nom, son type et sa valeur."
            ),
        },

        # ── TP8 : Fichiers et CSV ──
        {
            "title": "TP8 - Q1",
            "description": (
                "Créer un fichier mesures.txt avec with open(..., 'w') et y écrire les valeurs "
                "5.02, 4.98 et 5.01, une valeur par ligne. Puis afficher \"Fichier créé\"."
            ),
        },
        {
            "title": "TP8 - Q2",
            "description": (
                "Lire mesures.txt avec with open(..., 'r') et afficher chaque ligne sans ligne vide "
                "supplémentaire en utilisant strip()."
            ),
        },
        {
            "title": "TP8 - Q3",
            "description": (
                "Lire les nombres contenus dans mesures.txt, les convertir en float et calculer leur moyenne. "
                "Afficher la moyenne arrondie à 3 décimales."
            ),
        },
        {
            "title": "TP8 - Q4",
            "description": (
                "Créer mesures.csv avec le module csv. Écrire l'en-tête temps,tension puis les lignes "
                "0,5.0 ; 1,5.1 ; 2,4.9. Relire le fichier et afficher son contenu."
            ),
        },
        {
            "title": "TP8 - Q5",
            "description": (
                "Tenter d'ouvrir capteur.txt. Utiliser try/except FileNotFoundError pour afficher "
                "\"Fichier introuvable\" si le fichier n'existe pas."
            ),
        },

        # ── TP9 : NumPy et visualisation de signaux ──
        {
            "title": "TP9 - Q1",
            "description": (
                "Importer numpy. Créer avec np.linspace un vecteur t allant de 0 à 0.02 s contenant "
                "101 points. Afficher le nombre de points, la première et la dernière valeur."
            ),
        },
        {
            "title": "TP9 - Q2",
            "description": (
                "Avec numpy, générer u(t)=5*sin(2*pi*50*t) sur l'intervalle 0 à 0.04 s avec 1000 points. "
                "Afficher les valeurs minimale et maximale arrondies à 2 décimales."
            ),
        },
        {
            "title": "TP9 - Q3",
            "description": (
                "Tracer avec matplotlib le signal u(t)=5*sin(2*pi*50*t) entre 0 et 0.04 s. "
                "Ajouter un titre, les noms des axes et une grille, puis afficher le graphique."
            ),
        },
        {
            "title": "TP9 - Q4",
            "description": (
                "Tracer sur le même graphique deux signaux sinusoïdaux de fréquence 50 Hz : "
                "u1 d'amplitude 5 V et u2 d'amplitude 2 V. Ajouter une légende."
            ),
        },
        {
            "title": "TP9 - Q5",
            "description": (
                "Générer un signal sinusoïdal de fréquence 100 Hz et amplitude 3 V sur 0.02 s. "
                "Calculer avec numpy sa valeur efficace sqrt(mean(u**2)) et l'afficher arrondie à 3 décimales."
            ),
        },

        # ── TP10 : Projet de synthèse CIEL ──
        {
            "title": "TP10 - Q1",
            "description": (
                "Créer une fonction menu() qui affiche : 0-Quitter, 1-Loi d'Ohm, "
                "2-Diviseur de tension, 3-Résistance LED, puis retourne le choix saisi par l'utilisateur."
            ),
        },
        {
            "title": "TP10 - Q2",
            "description": (
                "Créer les fonctions loi_ohm(R,I), diviseur(Ue,R1,R2) et resistance_led(Ualim,Uled,I). "
                "Tester chacune avec un jeu de valeurs et afficher les résultats avec leurs unités."
            ),
        },
        {
            "title": "TP10 - Q3",
            "description": (
                "Construire une boucle while qui affiche le menu jusqu'au choix 0. "
                "Pour les choix 1 à 3, demander les valeurs nécessaires et appeler la bonne fonction. "
                "Afficher \"Choix invalide\" pour toute autre valeur."
            ),
        },
        {
            "title": "TP10 - Q4",
            "description": (
                "Ajouter à l'application un historique sous forme de liste. Après chaque calcul, "
                "ajouter une chaîne décrivant le calcul et son résultat. Au moment de quitter, afficher l'historique."
            ),
        },
        {
            "title": "TP10 - Q5",
            "description": (
                "Projet final : compléter l'application pour enregistrer l'historique dans resultats.txt "
                "au moment de quitter. Le programme doit utiliser des fonctions, une boucle, des conditions, "
                "une liste, des f-strings et un fichier. Structurer et commenter clairement le code."
            ),
        },
    ]
    conn = get_db()
    cur = conn.cursor()
    for ex in exercises:
        cur.execute("SELECT id FROM exercises WHERE title = %s", (ex["title"],))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO exercises (title, description, test_cases) VALUES (%s, %s, %s)",
                (ex["title"], ex["description"], "[]")
            )
    conn.commit()
    cur.close()
    conn.close()


init_db()
seed_exercises()


def check_teacher(x_teacher_password: Optional[str] = Header(None)):
    if x_teacher_password != TEACHER_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    return True


class TestCase(BaseModel):
    inputs: List[str] = []
    expected_output: str = ""
    label: str = ""

class ExerciseCreate(BaseModel):
    title: str
    description: str = ""
    deadline: Optional[str] = None
    test_cases: List[TestCase] = []

class SubmissionCreate(BaseModel):
    student_name: str
    class_id: str
    exercise_id: int
    code: str
    output: str = ""
    test_results: List[dict] = []
    tab_switches: int = 0

class CheatEvent(BaseModel):
    student_name: str
    class_id: str
    exercise_id: int

class GradeUpdate(BaseModel):
    grade: Optional[float] = None

class ClassCodeCreate(BaseModel):
    class_name: str


@app.get("/exercises")
def list_exercises():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, title, description, deadline, created_at FROM exercises ORDER BY title ASC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


@app.get("/exercises/{exercise_id}")
def get_exercise(exercise_id: int):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM exercises WHERE id=%s", (exercise_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    d = dict(row)
    d["test_cases"] = json.loads(d["test_cases"])
    return d


@app.post("/exercises", status_code=201)
def create_exercise(ex: ExerciseCreate, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO exercises (title, description, deadline, test_cases) VALUES (%s,%s,%s,%s) RETURNING id",
        (ex.title, ex.description, ex.deadline, json.dumps([t.dict() for t in ex.test_cases]))
    )
    new_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return {"id": new_id, "message": "Exercice créé"}


@app.put("/exercises/{exercise_id}")
def update_exercise(exercise_id: int, ex: ExerciseCreate, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE exercises SET title=%s, description=%s, deadline=%s, test_cases=%s WHERE id=%s",
        (ex.title, ex.description, ex.deadline, json.dumps([t.dict() for t in ex.test_cases]), exercise_id)
    )
    conn.commit(); cur.close(); conn.close()
    return {"message": "Exercice mis à jour"}


@app.delete("/exercises/{exercise_id}")
def delete_exercise(exercise_id: int, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM exercises WHERE id=%s", (exercise_id,))
    conn.commit(); cur.close(); conn.close()
    return {"message": "Exercice supprimé"}


@app.post("/cheat-event", status_code=201)
def report_cheat_event(ev: CheatEvent):
    """Enregistre un changement de page côté serveur — résistant aux modifications DevTools."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cheat_events (student_name, class_id, exercise_id, count)
        VALUES (%s, %s, %s, 1)
        ON CONFLICT (student_name, class_id, exercise_id)
        DO UPDATE SET count = cheat_events.count + 1, updated_at = CURRENT_TIMESTAMP
        RETURNING count
    """, (ev.student_name, ev.class_id, ev.exercise_id))
    count = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return {"count": count}


@app.post("/submit", status_code=201)
def submit(sub: SubmissionCreate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM exercises WHERE id=%s", (sub.exercise_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    # Une seule soumission par élève par exercice
    cur.execute(
        "SELECT id FROM submissions WHERE student_name=%s AND class_id=%s AND exercise_id=%s",
        (sub.student_name, sub.class_id, sub.exercise_id)
    )
    if cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(status_code=409, detail="Exercice déjà soumis")
    cur.execute(
            "INSERT INTO submissions (student_name, class_id, exercise_id, code, output, test_results, tab_switches) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (sub.student_name, sub.class_id, sub.exercise_id, sub.code, sub.output, json.dumps(sub.test_results), sub.tab_switches)
        )
    new_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    # Correction automatique par l'IA
    note, commentaire = None, None
    try:
        note, commentaire = _run_auto_grade(new_id)
    except Exception:
        pass  # On ne bloque pas la soumission si l'IA échoue
    return {"message": "Soumission enregistrée", "note": note, "commentaire": commentaire}


@app.get("/submissions")
def list_submissions(
    exercise_id: Optional[int] = Query(None),
    class_id: Optional[str] = Query(None),
    student_name: Optional[str] = Query(None),
    auth=Depends(check_teacher),
):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    q = """
        SELECT s.*, e.title AS exercise_title
        FROM submissions s
        JOIN exercises e ON s.exercise_id = e.id
        WHERE 1=1
    """
    params = []
    if exercise_id:
        q += " AND s.exercise_id=%s"; params.append(exercise_id)
    if class_id:
        q += " AND s.class_id=%s"; params.append(class_id)
    if student_name:
        q += " AND s.student_name ILIKE %s"; params.append(f"%{student_name}%")
    q += " ORDER BY s.submitted_at DESC"
    cur.execute(q, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["test_results"] = json.loads(d["test_results"])
        d["grade"] = float(d["grade"]) if d["grade"] is not None else None
        result.append(d)
    return result


@app.get("/submissions/student")
def list_student_submissions(
    student_name: str = Query(...),
    class_id: str = Query(...),
):
    """Soumissions visibles par l'élève (sans auth) — uniquement ses propres données"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT s.id, s.exercise_id, s.code, s.output, s.test_results,
               s.grade, s.ai_comment, s.submitted_at, e.title AS exercise_title
        FROM submissions s
        JOIN exercises e ON s.exercise_id = e.id
        WHERE s.student_name ILIKE %s AND s.class_id = %s
        ORDER BY s.submitted_at DESC
    """, (student_name.strip(), class_id))
    rows = cur.fetchall()
    cur.close(); conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["test_results"] = json.loads(d["test_results"])
        d["grade"] = float(d["grade"]) if d["grade"] is not None else None
        result.append(d)
    return result


@app.patch("/submissions/{submission_id}/grade")
def set_grade(submission_id: int, body: GradeUpdate, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE submissions SET grade=%s WHERE id=%s", (body.grade, submission_id))
    conn.commit(); cur.close(); conn.close()
    return {"message": "Note enregistrée"}


@app.delete("/submissions/{submission_id}")
def delete_submission(submission_id: int, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM submissions WHERE id=%s", (submission_id,))
    conn.commit(); cur.close(); conn.close()
    return {"message": "Soumission supprimée"}


def _run_auto_grade(submission_id: int):
    """Appelle Claude pour noter une soumission. Retourne (note, commentaire) ou lève une exception."""
    import re
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT s.code, s.output, s.tab_switches, s.student_name, s.class_id, s.exercise_id,
               e.title, e.description
        FROM submissions s
        JOIN exercises e ON s.exercise_id = e.id
        WHERE s.id = %s
    """, (submission_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise ValueError("Soumission introuvable")

    # Utiliser le compte serveur (résistant aux modifications DevTools)
    cur.execute(
        "SELECT count FROM cheat_events WHERE student_name=%s AND class_id=%s AND exercise_id=%s",
        (row["student_name"], row["class_id"], row["exercise_id"])
    )
    cheat_row = cur.fetchone()
    tab_switches = cheat_row["count"] if cheat_row else (row.get("tab_switches") or 0)

    # Si l'élève a changé de page 2 fois ou plus, note 0 directement sans appel IA
    if tab_switches >= 2:
        note = 0.0
        commentaire = "Note 0 : l'élève a changé de page 2 fois ou plus pendant l'exercice (détection anti-triche). Soumission non évaluée."
        cur2 = conn.cursor()
        cur2.execute(
            "UPDATE submissions SET grade=%s, ai_comment=%s WHERE id=%s",
            (note, commentaire, submission_id)
        )
        conn.commit()
        cur2.close(); cur.close(); conn.close()
        return note, commentaire

    tab_warning = ""
    if tab_switches == 1:
        tab_warning = "\n\nATTENTION : l'élève a changé de page 1 fois pendant l'exercice (détection anti-triche). Enlève 1 point à la note (minimum 0) et mentionne-le explicitement dans le commentaire."

    prompt = f"""Tu es un professeur de Python bienveillant au lycée. Évalue ce code d'élève.

Exercice : {row['title']}
Énoncé : {row['description']}

Code de l'élève :
```python
{row['code']}
```

Sortie produite par le programme :
{row['output'] or '(aucune sortie)'}{tab_warning}

Réponds UNIQUEMENT en JSON avec ce format exact :
{{"note": 0.0, "commentaire": "..."}}

- note : valeur parmi 0, 0.5, 1, 1.5 ou 2
- commentaire : 2 à 3 phrases en français. Mentionne ce qui est réussi, ce qui manque ou est incorrect, et un conseil si la note n'est pas maximale.
"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError("Réponse JSON invalide")
    data = json.loads(match.group())
    note = float(data["note"])
    if tab_switches == 1:
        note = max(0, note - 1)
    note = max(0, min(2, note))
    commentaire = str(data.get("commentaire", ""))

    cur2 = conn.cursor()
    cur2.execute(
        "UPDATE submissions SET grade=%s, ai_comment=%s WHERE id=%s",
        (note, commentaire, submission_id)
    )
    conn.commit()
    cur2.close()
    cur.close()
    conn.close()
    return note, commentaire


@app.post("/submissions/{submission_id}/auto-grade")
def auto_grade(submission_id: int, auth=Depends(check_teacher)):
    try:
        note, commentaire = _run_auto_grade(submission_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur IA : {str(e)}")
    return {"note": note, "commentaire": commentaire}


def _generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@app.get("/class-codes/verify")
def verify_class_code(code: str = Query(...)):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM class_codes WHERE code=%s", (code.upper(),))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Code invalide")
    return dict(row)


@app.get("/class-codes")
def list_class_codes(auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM class_codes ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


@app.post("/class-codes", status_code=201)
def create_class_code(body: ClassCodeCreate, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    for _ in range(10):
        code = _generate_code()
        try:
            cur.execute(
                "INSERT INTO class_codes (code, class_name) VALUES (%s, %s) RETURNING id",
                (code, body.class_name)
            )
            new_id = cur.fetchone()[0]
            conn.commit(); cur.close(); conn.close()
            return {"id": new_id, "code": code, "class_name": body.class_name}
        except Exception:
            conn.rollback()
    cur.close(); conn.close()
    raise HTTPException(status_code=500, detail="Impossible de générer un code unique")


@app.delete("/class-codes/{code_id}")
def delete_class_code(code_id: int, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM class_codes WHERE id=%s", (code_id,))
    conn.commit(); cur.close(); conn.close()
    return {"message": "Code supprimé"}


@app.get("/stats")
def stats(auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM submissions"); total_sub = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM exercises");  total_ex  = cur.fetchone()[0]
    cur.execute("SELECT DISTINCT class_id FROM submissions"); classes = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()
    return {"total_submissions": total_sub, "total_exercises": total_ex, "classes": classes}

@app.get("/health")
def health():
 """Endpoint de healthcheck Koyeb — ne touche pas la BDD."""
 return {"status": "ok"}
