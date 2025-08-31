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

# Data models
class ItemIn(BaseModel):
    name: str

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

# List items with preview
@app.get("/items")
def get_items(limit: int = 50, offset: int = 0, preview_len: int = 200):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, SUBSTR(name,1,?) as preview FROM items LIMIT ? OFFSET ?", 
              (preview_len, limit, offset))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "preview": r[1]} for r in rows]

# Get full item
@app.get("/items/{item_id}")
def get_item(item_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": row[0], "name": row[1]}

# Add item
@app.post("/items")
def add_item(item: ItemIn):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO items (name) VALUES (?)", (item.name,))
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return {"id": item_id, "preview": item.name[:200]}

# Delete item
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}
