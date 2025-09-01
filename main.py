import uuid
import asyncio
from typing import Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, PlainTextResponse, StreamingResponse
import io

app = FastAPI()

# CORS open
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store
_items: Dict[str, str] = {}
_lock = asyncio.Lock()  # protect writes only

MAX_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

@app.get("/")
async def root():
    return ORJSONResponse({"message": "Backend is running"})

@app.get("/ping", status_code=204)
async def ping():
    return PlainTextResponse(status_code=204)

@app.get("/items")
async def get_items():
    # Lock-free read
    return ORJSONResponse(list(_items.keys()))

@app.post("/items")
async def create_item(request: Request):
    # Direct body bytes, geen JSON parsing
    body_bytes = await request.body()
    if len(body_bytes) > MAX_PAYLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Payload too large")
    payload = body_bytes.decode("utf-8")

    item_id = str(uuid.uuid4())
    # Lock alleen voor schrijven
    async with _lock:
        _items[item_id] = payload

    # Return alleen ID, geen payload → geen extra CPU
    return ORJSONResponse({"id": item_id})

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    payload = _items.get(item_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # Stream de string direct naar client
    return StreamingResponse(io.BytesIO(payload.encode("utf-8")), media_type="text/plain")

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    async with _lock:
        if item_id in _items:
            del _items[item_id]
            return ORJSONResponse({"status": "deleted"})
    raise HTTPException(status_code=404, detail="Item not found")
