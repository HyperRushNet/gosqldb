from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import secrets
import time

app = FastAPI()
DB_FILE = "data.db"

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class ItemIn(BaseModel):
    name: str

class ItemUpdate(BaseModel):
    name: str

# --- DB init ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Generate unique ID ---
def generate_id():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    while True:
        rand_id = secrets.token_hex(16)
        c.execute("SELECT 1 FROM items WHERE id=?", (rand_id,))
        if not c.fetchone():
            break
    conn.close()
    return rand_id

# --- Rate limiting (25 req/sec per client) ---
VISITS = {}
MAX_REQ = 25
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client = request.client.host
    now = time.time()
    VISITS.setdefault(client, [])
    VISITS[client] = [t for t in VISITS[client] if now - t < 1]
    if len(VISITS[client]) >= MAX_REQ:
        return Response("Too Many Requests", status_code=429)
    VISITS[client].append(now)
    return await call_next(request)

# --- Ultra-light ping ---
PING_RESPONSE = Response(status_code=204)
@app.get("/ping")
def ping():
    return PING_RESPONSE

# --- CRUD / Search / Health ---
@app.post("/items")
def add_item(item: ItemIn):
    item_id = generate_id()
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO items (id, name) VALUES (?, ?)", (item_id, item.name))
    conn.commit()
    conn.close()
    return {"id": item_id}

@app.get("/items/{item_id}")
def get_item(item_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Item not found")
    return {"id": item_id, "name": row[0]}

@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/items/{item_id}")
def update_item(item_id: str, item: ItemUpdate):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE items SET name=? WHERE id=?", (item.name, item_id))
    conn.commit()
    updated = c.rowcount
    conn.close()
    if not updated:
        raise HTTPException(404, "Item not found")
    return {"id": item_id, "name": item.name}

@app.get("/items")
def list_item_ids():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM items")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return {"ids": ids}

@app.get("/search")
def search_items(q: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM items WHERE name LIKE ?", (f"%{q}%",))
    results = [{"id": r[0], "name": r[1]} for r in c.fetchall()]
    conn.close()
    return results

@app.get("/health")
def health():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM items")
    count = c.fetchone()[0]
    conn.close()
    return {"status": "ok", "item_count": count}
