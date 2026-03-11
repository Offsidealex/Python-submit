from fastapi import FastAPI, HTTPException, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import json
import os
from datetime import datetime

app = FastAPI(title="Python Submit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Remplacer par votre URL GitHub Pages en production
    allow_methods=["*"],
    allow_headers=["*"],
)

TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "diderot2024")
DB_PATH = os.getenv("DB_PATH", "submissions.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            deadline TEXT,
            test_cases TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            class_id TEXT NOT NULL,
            exercise_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            output TEXT DEFAULT '',
            test_results TEXT DEFAULT '[]',
            submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        )
    """)
    conn.commit()
    conn.close()


init_db()


def check_teacher(x_teacher_password: Optional[str] = Header(None)):
    if x_teacher_password != TEACHER_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    return True


# ── Modèles ──────────────────────────────────────────────────────────────────

class TestCase(BaseModel):
    inputs: List[str] = []        # valeurs retournées par input() une à une
    expected_output: str = ""     # sortie stdout attendue (strip appliqué)
    label: str = ""               # ex: "Test 1 : n=5"

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
    test_results: List[dict] = []   # rempli côté client (Pyodide)


# ── Exercices ─────────────────────────────────────────────────────────────────

@app.get("/exercises")
def list_exercises():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, description, deadline, created_at FROM exercises ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/exercises/{exercise_id}")
def get_exercise(exercise_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM exercises WHERE id=?", (exercise_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    d = dict(row)
    d["test_cases"] = json.loads(d["test_cases"])
    return d


@app.post("/exercises", status_code=201)
def create_exercise(ex: ExerciseCreate, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO exercises (title, description, deadline, test_cases) VALUES (?,?,?,?)",
        (ex.title, ex.description, ex.deadline, json.dumps([t.dict() for t in ex.test_cases]))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, "message": "Exercice créé"}


@app.put("/exercises/{exercise_id}")
def update_exercise(exercise_id: int, ex: ExerciseCreate, auth=Depends(check_teacher)):
    conn = get_db()
    conn.execute(
        "UPDATE exercises SET title=?, description=?, deadline=?, test_cases=? WHERE id=?",
        (ex.title, ex.description, ex.deadline, json.dumps([t.dict() for t in ex.test_cases]), exercise_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Exercice mis à jour"}


@app.delete("/exercises/{exercise_id}")
def delete_exercise(exercise_id: int, auth=Depends(check_teacher)):
    conn = get_db()
    conn.execute("DELETE FROM exercises WHERE id=?", (exercise_id,))
    conn.execute("DELETE FROM submissions WHERE exercise_id=?", (exercise_id,))
    conn.commit()
    conn.close()
    return {"message": "Exercice supprimé"}


# ── Soumissions ───────────────────────────────────────────────────────────────

@app.post("/submit", status_code=201)
def submit(sub: SubmissionCreate):
    conn = get_db()
    ex = conn.execute("SELECT id FROM exercises WHERE id=?", (sub.exercise_id,)).fetchone()
    if not ex:
        conn.close()
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    conn.execute(
        "INSERT INTO submissions (student_name, class_id, exercise_id, code, output, test_results) VALUES (?,?,?,?,?,?)",
        (sub.student_name, sub.class_id, sub.exercise_id,
         sub.code, sub.output, json.dumps(sub.test_results))
    )
    conn.commit()
    conn.close()
    return {"message": "Soumission enregistrée"}


@app.get("/submissions")
def list_submissions(
    exercise_id: Optional[int] = Query(None),
    class_id: Optional[str] = Query(None),
    student_name: Optional[str] = Query(None),
    auth=Depends(check_teacher),
):
    conn = get_db()
    q = """
        SELECT s.*, e.title AS exercise_title
        FROM submissions s
        JOIN exercises e ON s.exercise_id = e.id
        WHERE 1=1
    """
    params: list = []
    if exercise_id:
        q += " AND s.exercise_id=?"; params.append(exercise_id)
    if class_id:
        q += " AND s.class_id=?"; params.append(class_id)
    if student_name:
        q += " AND s.student_name LIKE ?"; params.append(f"%{student_name}%")
    q += " ORDER BY s.submitted_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["test_results"] = json.loads(d["test_results"])
        result.append(d)
    return result


@app.delete("/submissions/{submission_id}")
def delete_submission(submission_id: int, auth=Depends(check_teacher)):
    conn = get_db()
    conn.execute("DELETE FROM submissions WHERE id=?", (submission_id,))
    conn.commit()
    conn.close()
    return {"message": "Soumission supprimée"}


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/stats")
def stats(auth=Depends(check_teacher)):
    conn = get_db()
    total_sub = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    total_ex  = conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
    classes   = conn.execute("SELECT DISTINCT class_id FROM submissions").fetchall()
    conn.close()
    return {
        "total_submissions": total_sub,
        "total_exercises": total_ex,
        "classes": [r[0] for r in classes],
    }
