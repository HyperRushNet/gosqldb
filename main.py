from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()
DB_FILE = "data.db"

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# List items with pagination
@app.get("/items")
def get_items(skip: int = 0, limit: int = 100):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM items ORDER BY id DESC LIMIT ? OFFSET ?", (limit, skip))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

# Add item
@app.post("/items")
def add_item(name: str = Query(...)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO items (name) VALUES (?)", (name,))
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return {"id": item_id, "name": name}

# Delete item
@app.post("/items/delete")
def delete_item(id: int = Query(...)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}
