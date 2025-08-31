from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()
DB_FILE = "data.db"

# --- CORS instellen ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # alles toestaan
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database initialiseren ---
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

# --- Helper functies ---
def get_all_items():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM items")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

def insert_item(name: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO items (name) VALUES (?)", (name,))
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return item_id

def delete_item(item_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


# --- Endpoints: Toevoegen ---
@app.post("/items")
def add_item(name: str = Query(...), full: bool = Query(False)):
    item_id = insert_item(name)
    if full:
        return get_all_items()  # full response
    return {"status": "ok", "id": item_id}  # minimal response

# --- Endpoints: Verwijderen ---
@app.delete("/items")
def remove_item(id: int = Query(...), full: bool = Query(False)):
    delete_item(id)
    if full:
        return get_all_items()  # full response
    return {"status": "ok"}  # minimal response

# --- Endpoint: Alle items ophalen ---
@app.get("/items")
def list_items():
    return get_all_items()
