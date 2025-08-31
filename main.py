from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite
import asyncio

app = FastAPI()
DB_FILE = "data.db"

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection
db_conn: aiosqlite.Connection = None

@app.on_event("startup")
async def startup():
    global db_conn
    db_conn = await aiosqlite.connect(DB_FILE)
    await db_conn.execute("PRAGMA journal_mode=WAL;")
    await db_conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
    """)
    await db_conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON items(name);")
    await db_conn.commit()

@app.on_event("shutdown")
async def shutdown():
    await db_conn.close()

@app.get("/items")
async def get_items():
    cursor = await db_conn.execute("SELECT id, name FROM items")
    rows = await cursor.fetchall()
    await cursor.close()
    return [{"id": r[0], "name": r[1]} for r in rows]

@app.post("/items")
async def add_item(name: str = Query(...), full: bool = Query(False)):
    cursor = await db_conn.execute("INSERT INTO items (name) VALUES (?)", (name,))
    if full:
        await db_conn.commit()
        cursor2 = await db_conn.execute("SELECT id, name FROM items")
        rows = await cursor2.fetchall()
        await cursor2.close()
        return [{"id": r[0], "name": r[1]} for r in rows]
    await db_conn.commit()
    return {"status": "ok"}

@app.delete("/items")
async def delete_item(id: int = Query(...), full: bool = Query(False)):
    await db_conn.execute("DELETE FROM items WHERE id = ?", (id,))
    if full:
        await db_conn.commit()
        cursor = await db_conn.execute("SELECT id, name FROM items")
        rows = await cursor.fetchall()
        await cursor.close()
        return [{"id": r[0], "name": r[1]} for r in rows]
    await db_conn.commit()
    return {"status": "ok"}
