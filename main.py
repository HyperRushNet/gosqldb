import uuid
import asyncio
from typing import Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, StreamingResponse

app = FastAPI()

# CORS open
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store (bytes, direct)
_items: Dict[str, bytes] = {}
_lock = asyncio.Lock()  # protect writes only

MAX_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

@app.get("/")
async def root():
    return ORJSONResponse({"message": "Backend is running"})

@app.get("/ping", status_code=204)
async def ping():
    return ORJSONResponse(status_code=204)

@app.get("/items")
async def get_items():
    # Lock-free read, alleen keys
    return ORJSONResponse(list(_items.keys()))

@app.post("/items")
async def create_item(request: Request):
    # Stream upload direct naar bytes (geen decode)
    size = 0
    body = bytearray()
    
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_PAYLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Payload too large")
        body.extend(chunk)

    item_id = str(uuid.uuid4())
    async with _lock:
        _items[item_id] = bytes(body)  # direct opslaan als bytes

    return ORJSONResponse({"id": item_id})

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    payload = _items.get(item_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # Stream direct uit bytes → geen extra RAM/CPU
    return StreamingResponse(iter([payload]), media_type="text/plain")

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    async with _lock:
        if item_id in _items:
            del _items[item_id]
            return ORJSONResponse({"status": "deleted"})
    raise HTTPException(status_code=404, detail="Item not found")
