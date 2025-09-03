from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import databases
import sqlalchemy
import datetime

DATABASE_URL = "sqlite:///./test.db"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

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

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/add")
async def add_item(item: Item):
    query = items.insert().values(id=item.id, content=item.content, created_at=datetime.datetime.utcnow())
    await database.execute(query)
    return {"status": "ok", "id": item.id}

@app.get("/get/{item_id}")
async def get_item(item_id: str):
    query = items.select().where(items.c.id == item_id)
    row = await database.fetch_one(query)
    if row:
        return {"id": row["id"], "content": row["content"], "created_at": row["created_at"]}
    return {"error": "Item not found"}

@app.get("/all")
async def get_all_items():
    query = items.select()
    rows = await database.fetch_all(query)
    return [{"id": row["id"], "content": row["content"], "created_at": row["created_at"]} for row in rows]
