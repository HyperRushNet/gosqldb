import asyncio
import uuid
from typing import Dict

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import ORJSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

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
_lock = asyncio.Lock()  # protect writes

MAX_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

@app.get("/")
async def root():
    return ORJSONResponse({"message": "Backend is running"})

@app.get("/ping", status_code=204)
async def ping():
    return Response(status_code=204)

@app.get("/items")
async def get_items():
    return ORJSONResponse(list(_items.keys()))

@app.post("/items")
async def create_item(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    payload = body.get("payload")
    if not isinstance(payload, str) or payload == "":
        raise HTTPException(status_code=400, detail="payload must be a non-empty string")

    # Check payload size (in bytes)
    size_bytes = len(payload.encode("utf-8"))
    if size_bytes > MAX_PAYLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Payload too large: {size_bytes} bytes (max {MAX_PAYLOAD_SIZE} bytes)"
        )

    item_id = str(uuid.uuid4())
    async with _lock:
        _items[item_id] = payload
    return ORJSONResponse({"id": item_id, "payload": payload})

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    payload = _items.get(item_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return PlainTextResponse(payload)

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    async with _lock:
        if item_id in _items:
            del _items[item_id]
            return ORJSONResponse({"status": "deleted"})
    raise HTTPException(status_code=404, detail="Item not found")
