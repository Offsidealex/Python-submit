from fastapi import FastAPI, HTTPException, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
import psycopg2.extras
import json
import os

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
        CREATE TABLE IF NOT EXISTS submissions (
            id SERIAL PRIMARY KEY,
            student_name TEXT NOT NULL,
            class_id TEXT NOT NULL,
            exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            output TEXT DEFAULT '',
            test_results TEXT DEFAULT '[]',
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


init_db()


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


@app.get("/exercises")
def list_exercises():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, title, description, deadline, created_at FROM exercises ORDER BY id DESC")
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


@app.post("/submit", status_code=201)
def submit(sub: SubmissionCreate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM exercises WHERE id=%s", (sub.exercise_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    cur.execute(
        "INSERT INTO submissions (student_name, class_id, exercise_id, code, output, test_results) VALUES (%s,%s,%s,%s,%s,%s)",
        (sub.student_name, sub.class_id, sub.exercise_id, sub.code, sub.output, json.dumps(sub.test_results))
    )
    conn.commit(); cur.close(); conn.close()
    return {"message": "Soumission enregistrée"}


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
        result.append(d)
    return result


@app.delete("/submissions/{submission_id}")
def delete_submission(submission_id: int, auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM submissions WHERE id=%s", (submission_id,))
    conn.commit(); cur.close(); conn.close()
    return {"message": "Soumission supprimée"}


@app.get("/stats")
def stats(auth=Depends(check_teacher)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM submissions"); total_sub = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM exercises");  total_ex  = cur.fetchone()[0]
    cur.execute("SELECT DISTINCT class_id FROM submissions"); classes = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()
    return {"total_submissions": total_sub, "total_exercises": total_ex, "classes": classes}
