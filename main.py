from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import databases
import sqlalchemy
import datetime
from fastapi.responses import StreamingResponse
from sqlalchemy import text
import logging

DATABASE_URL = "sqlite:///./data.db"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True
)

with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL;"))
    conn.execute(text("PRAGMA synchronous=NORMAL;"))

items = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("content", sqlalchemy.Text),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.datetime.utcnow),
)

metadata.create_all(engine)

app = FastAPI(title="Item Service", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_cors_origins(file_path: str = "cors.txt") -> list[str]:
    try:
        with open(file_path, "r") as f:
            origins = [
                line.strip() for line in f
                if line.strip() and not line.startswith("#")
            ]
            if "*" in origins:
                logger.info("CORS: allow all origins (*)")
                return ["*"]
            logger.info(f"CORS loaded: {origins}")
            return origins
    except FileNotFoundError:
        logger.warning(f"{file_path} not found. Allowing all origins.")
        return ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=load_cors_origins(),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

class Item(BaseModel):
    id: str
    content: str

@app.on_event("startup")
async def startup() -> None:
    await database.connect()
    logger.info("Database connected.")

@app.on_event("shutdown")
async def shutdown() -> None:
    await database.disconnect()
    logger.info("Database disconnected.")

@app.post("/add", response_model=dict)
async def add_item(item: Item) -> dict:
    query = items.insert().values(
        id=item.id,
        content=item.content,
        created_at=datetime.datetime.utcnow()
    )
    try:
        await database.execute(query)
        logger.info(f"Item added: {item.id}")
        return {"status": "ok", "id": item.id}
    except Exception as e:
        logger.error(f"Failed to add item {item.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add item")

@app.get("/items", response_model=list[str])
async def get_ids() -> list[str]:
    query = items.select().with_only_columns(items.c.id)
    rows = await database.fetch_all(query)
    return [row["id"] for row in rows]

@app.get("/items/{item_id}", response_class=StreamingResponse)
async def get_item_content(item_id: str) -> StreamingResponse:
    query = items.select().where(items.c.id == item_id)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    content: str = row["content"]
    def stream_chunks(data: str, chunk_size: int = 524288):
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]
    return StreamingResponse(stream_chunks(content), media_type="text/plain")

@app.get("/items/{item_id}/info", response_model=dict)
async def get_item_info(item_id: str) -> dict:
    query = items.select().where(items.c.id == item_id)
    row = await database.fetch_one(query)
    if row:
        return {"id": row["id"], "created_at": row["created_at"]}
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}", response_model=dict)
async def delete_item(item_id: str) -> dict:
    query = items.delete().where(items.c.id == item_id)
    result = await database.execute(query)
    if result:
        logger.info(f"Item deleted: {item_id}")
        return {"status": "deleted", "id": item_id}
    raise HTTPException(status_code=404, detail="Item not found")
