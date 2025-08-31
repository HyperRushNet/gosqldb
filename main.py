from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# Pydantic models voor POST body
class Item(BaseModel):
    name: str

class ItemDelete(BaseModel):
    id: int

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

# List items (GET, met skip/limit voor pagination)
@app.get("/items")
def get_items(skip: int = 0, limit: int = 100):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM items ORDER BY id DESC LIMIT ? OFFSET ?", (limit, skip))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

# Add item (POST, naam in body)
@app.post("/items")
def add_item(item: Item):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO items (name) VALUES (?)", (item.name,))
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return {"id": item_id, "name": item.name}

# Delete item (POST, id in body)
@app.post("/items/delete")
def delete_item(item: ItemDelete):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ?", (item.id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}
