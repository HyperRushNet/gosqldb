from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Column, Integer, String, LargeBinary, create_engine, MetaData, Table
from databases import Database
import datetime

DATABASE_URL = "sqlite:///./data.db"
database = Database(DATABASE_URL)
metadata = MetaData()

# Table definition
data_table = Table(
    "data",
    metadata,
    Column("id", String, primary_key=True),
    Column("content", LargeBinary),
    Column("created_at", String)
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

app = FastAPI()

# ----------------------
# CORS
# ----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Startup/Shutdown
# ----------------------
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ----------------------
# Ping endpoint
# ----------------------
@app.get("/ping")
async def ping():
    return {"status": "ok"}

# ----------------------
# Upload data
# ----------------------
@app.post("/upload")
async def upload_data(id: str = Form(...), file: UploadFile = None, text: str = Form(None)):
    if file:
        content = await file.read()
    elif text:
        content = text.encode()
    else:
        raise HTTPException(status_code=400, detail="No content provided")

    query = data_table.insert().values(
        id=id,
        content=content,
        created_at=str(datetime.datetime.utcnow())
    )
    await database.execute(query)
    return {"message": f"Data stored under ID {id}"}

# ----------------------
# Get data by ID
# ----------------------
@app.get("/data/{id}")
async def get_data(id: str):
    query = data_table.select().where(data_table.c.id == id)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="ID not found")
    return {"id": row["id"], "content": row["content"].decode(), "created_at": row["created_at"]}

# ----------------------
# List all IDs
# ----------------------
@app.get("/ids")
async def list_ids():
    query = data_table.select()
    rows = await database.fetch_all(query)
    return {"ids": [row["id"] for row in rows]}
