from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import databases
import sqlalchemy
import datetime
import zlib
from fastapi.responses import StreamingResponse

DATABASE_URL = "sqlite:///./data.db"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

items = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("content", sqlalchemy.LargeBinary),  # Gecomprimeerde BLOB
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.datetime.utcnow),
)

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    id: str
    content: str

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Voeg item toe
@app.post("/add")
async def add_item(item: Item):
    compressed = zlib.compress(item.content.encode("utf-8"))
    query = items.insert().values(
        id=item.id,
        content=compressed,
        created_at=datetime.datetime.utcnow()
    )
    await database.execute(query)
    return {"status": "ok", "id": item.id}

# Lijst van IDs
@app.get("/items")
async def get_ids():
    query = items.select().with_only_columns(items.c.id)
    rows = await database.fetch_all(query)
    return [row["id"] for row in rows]

# Stream content van item (RAM-efficient)
@app.get("/items/{item_id}")
async def get_item_content(item_id: str):
    query = items.select().where(items.c.id == item_id)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    compressed = row["content"]

    def decompress_chunks(data, chunk_size=65536):
        decompress_obj = zlib.decompressobj()
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            yield decompress_obj.decompress(chunk)
        yield decompress_obj.flush()

    return StreamingResponse(decompress_chunks(compressed), media_type="text/plain")

# Metadata van item
@app.get("/items/{item_id}/info")
async def get_item_info(item_id: str):
    query = items.select().where(items.c.id == item_id)
    row = await database.fetch_one(query)
    if row:
        return {"id": row["id"], "created_at": row["created_at"]}
    raise HTTPException(status_code=404, detail="Item not found")

# Delete item
@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    query = items.delete().where(items.c.id == item_id)
    result = await database.execute(query)
    if result:
        return {"status": "deleted", "id": item_id}
    raise HTTPException(status_code=404, detail="Item not found")
