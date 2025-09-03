from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlalchemy
import databases

# ----------------------
# Config
# ----------------------
DATABASE_URL = "sqlite:///./data.db"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# SQLite table
items = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("data", sqlalchemy.LargeBinary),
)

engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # alles toegestaan
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Startup / Shutdown
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
    return JSONResponse({"status": "ok"})

# ----------------------
# CreateWS endpoint
# ----------------------
@app.get("/createws")
async def create_ws():
    return JSONResponse({"message": "WS ready"})

# ----------------------
# WebSocket endpoint
# ----------------------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    buffer = b""  # accumulate all chunks

    while True:
        try:
            msg = await ws.receive_bytes()
        except:
            continue

        try:
            text = msg.decode()
        except:
            text = None

        # NEW ID
        if text and text.startswith("NEWID:"):
            current_id = text[6:]
            buffer = b""
            await ws.send_text(f"READY:{current_id}")

        # GET
        elif text and text.startswith("GET:"):
            item_id = text[4:]
            query = items.select().where(items.c.id == item_id)
            item = await database.fetch_one(query)
            if item:
                await ws.send_bytes(item["data"])
                await ws.send_text(f"END:{item_id}")
            else:
                await ws.send_text("ERROR:NOT_FOUND")

        # ENDUPLOAD
        elif text and text.startswith("ENDUPLOAD:"):
            end_id = text[10:]
            if end_id == current_id:
                query = items.insert().values(id=current_id, data=buffer)
                await database.execute(query)
                await ws.send_text(f"ADDED:{current_id}")
                buffer = b""
            else:
                await ws.send_text("ERROR:UPLOAD_MISMATCH")

        # Payload chunk
        else:
            if current_id:
                buffer += msg
