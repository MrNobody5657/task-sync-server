from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from typing import List
import uvicorn

app = FastAPI()

# Разрешаем нашему PWA-приложению делать запросы к серверу
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Пока разрешаем всем (для разработки)
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "tasks.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            priority TEXT DEFAULT 'med',
            progress INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Модель данных для получения новой задачи
class TaskCreate(BaseModel):
    title: str
    priority: str
    progress: int
    created_at: str

# Модель данных для обновления задачи
class TaskUpdate(BaseModel):
    id: int
    progress: int
    priority: str

@app.get("/api/tasks", response_model=List[dict])
def get_tasks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/tasks")
def create_task(task: TaskCreate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (title, priority, progress, created_at) VALUES (?, ?, ?, ?)",
        (task.title, task.priority, task.progress, task.created_at)
    )
    conn.commit()
    task_id = c.lastrowid
    conn.close()
    return {"id": task_id, "status": "ok"}

@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE tasks SET progress = ?, priority = ? WHERE id = ?",
        (task.progress, task.priority, task_id)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

if __name__ == "__main__":
    # Запускаем сервер на порту 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
