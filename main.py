from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import databases, sqlalchemy, datetime
from fastapi.responses import StreamingResponse
import os, hashlib, base64, hmac, asyncio, logging

# ---------- Database setup ----------
DATABASE_URL = "sqlite+aiosqlite:///./data.db"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

engine = sqlalchemy.create_engine(
    "sqlite:///./data.db",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

with engine.connect() as conn:
    conn.execute(sqlalchemy.text("PRAGMA journal_mode=WAL;"))
    conn.execute(sqlalchemy.text("PRAGMA synchronous=OFF;"))

rooms = sqlalchemy.Table(
    "rooms",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String)
)

items = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("room_id", sqlalchemy.String, index=True),
    sqlalchemy.Column("content", sqlalchemy.Text),
    sqlalchemy.Column("password_hash", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.datetime.utcnow)
)

metadata.create_all(engine)

# ---------- App setup ----------
app = FastAPI(title="Render Free Max Item Service", version="1.0.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET","POST","DELETE","PUT"],
    allow_headers=["*"]
)

# ---------- Models ----------
class Room(BaseModel):
    id: str
    name: str

class Item(BaseModel):
    id: str
    room_id: str
    content: str
    password: str | None = None

# ---------- Password helpers ----------
async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash_password_sync, password)

def _hash_password_sync(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return base64.b64encode(salt + hashed).decode("utf-8")

async def verify_password(password: str, hashed_str: str) -> bool:
    return await asyncio.to_thread(_verify_password_sync, password, hashed_str)

def _verify_password_sync(password: str, hashed_str: str) -> bool:
    data = base64.b64decode(hashed_str.encode("utf-8"))
    salt = data[:16]
    stored_hash = data[16:]
    check_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(stored_hash, check_hash)

# ---------- Events ----------
@app.on_event("startup")
async def startup():
    await database.connect()
    logger.info("DB connected")

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    logger.info("DB disconnected")

# ---------- Endpoints ----------
@app.get("/ping", status_code=204)
async def ping():
    return

@app.get("/rooms", response_model=list[dict])
async def list_rooms():
    rows = await database.fetch_all(rooms.select())
    return [{"id": r["id"], "name": r["name"]} for r in rows]

@app.post("/rooms", response_model=dict)
async def create_room(room: Room):
    exists = await database.fetch_one(rooms.select().where(rooms.c.id == room.id))
    if exists:
        raise HTTPException(400, detail="Room already exists")
    await database.execute(rooms.insert().values(id=room.id, name=room.name))
    return {"status":"ok","id":room.id}

@app.delete("/rooms/{room_id}/delete", response_model=dict)
async def delete_room(room_id: str):
    room = await database.fetch_one(rooms.select().where(rooms.c.id == room_id))
    if not room:
        raise HTTPException(404, detail="Room not found")

    has_pw_items = await database.fetch_one(
        items.select()
        .where((items.c.room_id == room_id) & (items.c.password_hash.isnot(None)))
        .limit(1)
    )
    if has_pw_items:
        raise HTTPException(
            403,
            detail="Room contains password-protected items and cannot be deleted"
        )

    await database.execute(items.delete().where(items.c.room_id == room_id))
    await database.execute(rooms.delete().where(rooms.c.id == room_id))
    return {"status": "deleted", "room_id": room_id}

@app.post("/rooms/{room_id}/items", response_model=dict)
async def add_item(room_id: str, item: Item):
    room = await database.fetch_one(rooms.select().where(rooms.c.id == room_id))
    if not room:
        raise HTTPException(404, detail="Room not found")

    pw_hash = await hash_password(item.password) if item.password else None
    await database.execute(items.insert().values(
        id=item.id, room_id=room_id, content=item.content,
        password_hash=pw_hash, created_at=datetime.datetime.utcnow()
    ))
    return {"status":"ok","id":item.id}

@app.get("/rooms/{room_id}/items", response_model=list[str])
async def list_items(room_id: str):
    room = await database.fetch_one(rooms.select().where(rooms.c.id == room_id))
    if not room:
        raise HTTPException(404, detail="Room not found")
    rows = await database.fetch_all(
        items.select().where(items.c.room_id == room_id).with_only_columns(items.c.id)
    )
    return [r["id"] for r in rows]

@app.get("/rooms/{room_id}/items/{item_id}", response_class=StreamingResponse)
async def get_item(room_id: str, item_id: str, password: str | None = None):
    row = await database.fetch_one(items.select().where(
        (items.c.id == item_id) & (items.c.room_id == room_id)
    ))
    if not row:
        raise HTTPException(404, detail="Item not found")
    if row["password_hash"]:
        if not password or not await verify_password(password, row["password_hash"]):
            raise HTTPException(403, detail="Wrong password")

    def stream_chunks(data: str, chunk_size: int = 524288):
        for i in range(0, len(data), chunk_size):
            yield data[i:i+chunk_size]

    return StreamingResponse(stream_chunks(row["content"]), media_type="text/plain")

@app.get("/rooms/{room_id}/items/{item_id}/info", response_model=dict)
async def get_item_info(room_id: str, item_id: str, password: str | None = None):
    row = await database.fetch_one(items.select().where(
        (items.c.id == item_id) & (items.c.room_id == room_id)
    ))
    if not row:
        raise HTTPException(404, detail="Item not found")
    if row["password_hash"]:
        if not password or not await verify_password(password, row["password_hash"]):
            raise HTTPException(403, detail="Wrong password")
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "has_password": bool(row["password_hash"])
    }

@app.put("/rooms/{room_id}/items/{item_id}/edit", response_model=dict)
async def edit_item(room_id: str, item_id: str, content: str, password: str | None = None):
    row = await database.fetch_one(items.select().where(
        (items.c.id == item_id) & (items.c.room_id == room_id)
    ))
    if not row:
        raise HTTPException(404, detail="Item not found")
    if row["password_hash"]:
        if not password or not await verify_password(password, row["password_hash"]):
            raise HTTPException(403, detail="Wrong password")

    await database.execute(items.update().where(
        (items.c.id == item_id) & (items.c.room_id == room_id)
    ).values(content=content))
    return {"status":"ok","id":item_id}

@app.delete("/rooms/{room_id}/items/{item_id}/delete", response_model=dict)
async def delete_item(room_id: str, item_id: str, password: str | None = None):
    row = await database.fetch_one(items.select().where(
        (items.c.id == item_id) & (items.c.room_id == room_id)
    ))
    if not row:
        raise HTTPException(404, detail="Item not found")
    if row["password_hash"]:
        if not password or not await verify_password(password, row["password_hash"]):
            raise HTTPException(403, detail="Wrong password")

    await database.execute(items.delete().where(
        (items.c.id == item_id) & (items.c.room_id == room_id)
    ))
    return {"status":"deleted","id":item_id}
