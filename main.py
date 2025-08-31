from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import secrets
import logging

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

# Models
class ItemIn(BaseModel):
    name: str

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Generate a unique random ID
def generate_unique_id():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    while True:
        rand_id = secrets.token_hex(16)  # 32-char hex string
        c.execute("SELECT 1 FROM items WHERE id=?", (rand_id,))
        if not c.fetchone():
            break
    conn.close()
    return rand_id

# Add item
@app.post("/items")
def add_item(item: ItemIn):
    item_id = generate_unique_id()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO items (id, name) VALUES (?, ?)", (item_id, item.name))
    conn.commit()
    conn.close()
    return {"id": item_id}

# Get item by ID
@app.get("/items/{item_id}")
def get_item(item_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, "name": row[0]}

# Delete item by ID
@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# --- Ultra-light PING endpoint ---
PING_RESPONSE = Response(status_code=204)

@app.get("/ping")
def ping():
    # Re-use the same Response object: no CPU, no body, ~200 bytes total
    return PING_RESPONSE


# --- Middleware: skip logs for /ping (saves I/O) ---
@app.middleware("http")
async def ignore_ping_logs(request: Request, call_next):
    if request.url.path == "/ping":
        logging.getLogger("uvicorn.access").disabled = True
    else:
        logging.getLogger("uvicorn.access").disabled = False
    return await call_next(request)
