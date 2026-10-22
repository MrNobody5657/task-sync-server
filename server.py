from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import sqlite3
from typing import List
import hashlib
import secrets

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = "tasks.db"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, token TEXT)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            priority TEXT DEFAULT 'med',
            progress INTEGER DEFAULT 0,
            created_at TEXT,
            subtasks TEXT DEFAULT '[]',
            repeat_type TEXT DEFAULT 'none',
            due_date TEXT DEFAULT '',
            attachment_url TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def hash_password(password: str): return hashlib.sha256(password.encode()).hexdigest()

def get_current_user(token: str = Depends(oauth2_scheme)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE token = ?", (token,))
    user = c.fetchone()
    conn.close()
    if not user: raise HTTPException(status_code=401, detail="Неверный токен")
    return user[0]

class UserCreate(BaseModel):
    email: str
    password: str

class TaskCreate(BaseModel):
    title: str
    priority: str
    progress: int
    created_at: str
    subtasks: str = '[]'
    repeat_type: str = 'none'
    due_date: str = ''
    attachment_url: str = ''

class TaskUpdate(BaseModel):
    id: int
    progress: int
    priority: str
    subtasks: str = '[]'
    repeat_type: str = 'none'
    due_date: str = ''
    attachment_url: str = ''

@app.post("/api/register")
def register(user: UserCreate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (user.email, hash_password(user.password)))
        conn.commit()
        return {"status": "ok"}
    except sqlite3.IntegrityError: raise HTTPException(status_code=400, detail="Email уже занят")
    finally: conn.close()

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ? AND password_hash = ?", (form_data.username, hash_password(form_data.password)))
    user = c.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=400, detail="Неверный email или пароль")
    token = secrets.token_hex(16)
    c.execute("UPDATE users SET token = ? WHERE id = ?", (token, user[0]))
    conn.commit(); conn.close()
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/tasks", response_model=List[dict])
def get_tasks(user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = c.fetchall(); conn.close()
    return [dict(row) for row in rows]

@app.post("/api/tasks")
def create_task(task: TaskCreate, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (user_id, title, priority, progress, created_at, subtasks, repeat_type, due_date, attachment_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, task.title, task.priority, task.progress, task.created_at, task.subtasks, task.repeat_type, task.due_date, task.attachment_url)
    )
    conn.commit(); task_id = c.lastrowid; conn.close()
    return {"id": task_id, "status": "ok"}

@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE tasks SET progress = ?, priority = ?, subtasks = ?, repeat_type = ?, due_date = ?, attachment_url = ? WHERE id = ? AND user_id = ?",
        (task.progress, task.priority, task.subtasks, task.repeat_type, task.due_date, task.attachment_url, task_id, user_id)
    )
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit(); conn.close()
    return {"status": "ok"}
