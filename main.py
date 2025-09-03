from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlalchemy
import databases
import datetime

DATABASE_URL = "sqlite:///./test.db"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# Table definition
items = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("content", sqlalchemy.Text),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.datetime.utcnow),
)

engine = sqlalchemy.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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

# Startup/shutdown
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# CRUD routes

# Add item
@app.post("/add")
async def add_item(item: Item):
    query = items.insert().values(id=item.id, content=item.content, created_at=datetime.datetime.utcnow())
    await database.execute(query)
    return {"status": "ok", "id": item.id}

# Get all IDs
@app.get("/items")
async def get_ids():
    query = items.select().with_only_columns([items.c.id])
    rows = await database.fetch_all(query)
    return [row["id"] for row in rows]

# Get content (plain text)
@app.get("/items/{item_id}")
async def get_content(item_id: str):
    query = items.select().where(items.c.id == item_id)
    row = await database.fetch_one(query)
    if row:
        return row["content"]
    raise HTTPException(status_code=404, detail="Item not found")

# Get info (JSON, excluding content)
@app.get("/items/{item_id}/info")
async def get_info(item_id: str):
    query = items.select().where(items.c.id == item_id)
    row = await database.fetch_one(query)
    if row:
        return {
            "id": row["id"],
            "created_at": row["created_at"]
        }
    raise HTTPException(status_code=404, detail="Item not found")

# Delete item
@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    query = items.delete().where(items.c.id == item_id)
    result = await database.execute(query)
    return {"status": "deleted", "id": item_id}
