from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import databases
import sqlalchemy
import datetime
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import text, func
from passlib.context import CryptContext
import io
import csv

DATABASE_URL = "sqlite:///./data.db"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True
)

with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL;"))
    conn.execute(text("PRAGMA synchronous=NORMAL;"))

rooms = sqlalchemy.Table(
    "rooms",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.datetime.utcnow),
)

items = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("room_id", sqlalchemy.String),
    sqlalchemy.Column("content", sqlalchemy.Text),
    sqlalchemy.Column("password_hash", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.datetime.utcnow),
)

metadata.create_all(engine)

app = FastAPI(title="Secure Hobby DB with Rooms", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Room(BaseModel):
    id: str
    name: str

class Item(BaseModel):
    id: str
    content: str
    password: str | None = None

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Rooms endpoints
@app.post("/rooms", response_model=dict)
async def create_room(room: Room):
    query = rooms.insert().values(id=room.id, name=room.name, created_at=datetime.datetime.utcnow())
    await database.execute(query)
    return {"status": "ok", "id": room.id}

@app.get("/rooms", response_model=list[dict])
async def list_rooms():
    query = rooms.select()
    rows = await database.fetch_all(query)
    return [{"id": r["id"], "name": r["name"], "created_at": r["created_at"]} for r in rows]

@app.get("/rooms/{room_id}", response_model=dict)
async def room_info(room_id: str):
    query = rooms.select().where(rooms.c.id == room_id)
    row = await database.fetch_one(query)
    if row:
        return {"id": row["id"], "name": row["name"], "created_at": row["created_at"]}
    raise HTTPException(status_code=404, detail="Room not found")

@app.delete("/rooms/{room_id}", response_model=dict)
async def delete_room(room_id: str):
    query = rooms.delete().where(rooms.c.id == room_id)
    result = await database.execute(query)
    if result:
        return {"status": "deleted", "id": room_id}
    raise HTTPException(status_code=404, detail="Room not found")

# Items endpoints
@app.post("/rooms/{room_id}/add", response_model=dict)
async def add_item(room_id: str, item: Item):
    password_hash = pwd_context.hash(item.password) if item.password else None
    query = items.insert().values(
        id=item.id,
        room_id=room_id,
        content=item.content,
        password_hash=password_hash,
        created_at=datetime.datetime.utcnow()
    )
    await database.execute(query)
    return {"status": "ok", "id": item.id, "room_id": room_id}

@app.put("/rooms/{room_id}/items/{item_id}/edit", response_model=dict)
async def edit_item(room_id: str, item_id: str, item: Item, password: str | None = None):
    query = items.select().where(items.c.room_id==room_id).where(items.c.id==item_id)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if row["password_hash"] and not (password and pwd_context.verify(password, row["password_hash"])):
        raise HTTPException(status_code=403, detail="Incorrect password")
    new_hash = pwd_context.hash(item.password) if item.password else row["password_hash"]
    update_query = items.update().where(items.c.id==item_id).values(content=item.content, password_hash=new_hash)
    await database.execute(update_query)
    return {"status": "ok", "id": item_id, "room_id": room_id}

@app.get("/rooms/{room_id}/items", response_model=list[str])
async def get_items_in_room(room_id: str):
    query = items.select().where(items.c.room_id == room_id).with_only_columns(items.c.id)
    rows = await database.fetch_all(query)
    return [r["id"] for r in rows]

@app.get("/rooms/{room_id}/items/{item_id}", response_class=StreamingResponse)
async def get_item_content(room_id: str, item_id: str, password: str | None = None):
    query = items.select().where(items.c.room_id==room_id).where(items.c.id==item_id)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if row["password_hash"] and not (password and pwd_context.verify(password, row["password_hash"])):
        raise HTTPException(status_code=403, detail="Incorrect password")
    content = row["content"]
    def stream_chunks(data: str, chunk_size: int = 524288):
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]
    return StreamingResponse(stream_chunks(content), media_type="text/plain")

@app.get("/rooms/{room_id}/items/{item_id}/info", response_model=dict)
async def get_item_info(room_id: str, item_id: str, password: str | None = None):
    query = items.select().where(items.c.room_id==room_id).where(items.c.id==item_id)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if row["password_hash"] and not (password and pwd_context.verify(password, row["password_hash"])):
        raise HTTPException(status_code=403, detail="Incorrect password")
    return {"id": row["id"], "room_id": row["room_id"], "created_at": row["created_at"], "length": len(row["content"])}

@app.delete("/rooms/{room_id}/items/{item_id}/delete", response_model=dict)
async def delete_item(room_id: str, item_id: str, password: str | None = None):
    query = items.select().where(items.c.room_id==room_id).where(items.c.id==item_id)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if row["password_hash"] and not (password and pwd_context.verify(password, row["password_hash"])):
        raise HTTPException(status_code=403, detail="Incorrect password")
    delete_query = items.delete().where(items.c.id==item_id)
    await database.execute(delete_query)
    return {"status": "deleted", "id": item_id, "room_id": room_id}

# Serious item endpoints per room
@app.get("/rooms/{room_id}/items/count", response_model=dict)
async def count_items(room_id: str):
    query = sqlalchemy.select([func.count()]).select_from(items).where(items.c.room_id==room_id)
    result = await database.fetch_val(query)
    return {"count": result}

@app.get("/rooms/{room_id}/items/recent", response_model=list[dict])
async def recent_items(room_id: str, limit: int = Query(10, ge=1, le=100)):
    query = items.select().where(items.c.room_id==room_id).order_by(items.c.created_at.desc()).limit(limit)
    rows = await database.fetch_all(query)
    return [{"id": r["id"], "created_at": r["created_at"], "length": len(r["content"])} for r in rows]

@app.get("/rooms/{room_id}/items/search", response_model=list[dict])
async def search_items(room_id: str, query: str = Query(..., min_length=1)):
    q = items.select().where(items.c.room_id==room_id).where(items.c.content.like(f"%{query}%"))
    rows = await database.fetch_all(q)
    return [{"id": r["id"], "created_at": r["created_at"], "length": len(r["content"])} for r in rows]

@app.get("/rooms/{room_id}/items/filter", response_model=list[dict])
async def filter_items(room_id: str, minlen: int = 0, maxlen: int = 1000000):
    q = items.select().where(items.c.room_id==room_id).where(items.c.content.length >= minlen).where(items.c.content.length <= maxlen)
    rows = await database.fetch_all(q)
    return [{"id": r["id"], "created_at": r["created_at"], "length": len(r["content"])} for r in rows]

@app.get("/rooms/{room_id}/items/stats", response_model=dict)
async def items_stats(room_id: str):
    query = items.select().where(items.c.room_id==room_id)
    rows = await database.fetch_all(query)
    lengths = [len(r["content"]) for r in rows]
    return {
        "count": len(rows),
        "min_length": min(lengths) if lengths else 0,
        "max_length": max(lengths) if lengths else 0,
        "avg_length": sum(lengths)//len(lengths) if lengths else 0
    }

@app.get("/rooms/{room_id}/items/export", response_class=Response)
async def export_items(room_id: str):
    query = items.select().where(items.c.room_id==room_id)
    rows = await database.fetch_all(query)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "created_at", "length", "content"])
    for r in rows:
        writer.writerow([r["id"], r["created_at"], len(r["content"]), r["content"]])
    return Response(content=output.getvalue(), media_type="text/csv")

# Ultra-light ping
ping_app = FastAPI()
ping_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"]
)
@ping_app.get("/")
async def ping():
    return Response(status_code=204)

app.mount("/ping", ping_app)
