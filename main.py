from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()
DB_FILE = "data.db"

# Enable CORS
origins = ["*"]  # alles toestaan; voor productie kun je specifieke domains zetten
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

@app.get("/items")
def get_items():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM items")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

@app.post("/items")
def add_item(name: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO items (name) VALUES (?)", (name,))
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return {"id": item_id, "name": name}
