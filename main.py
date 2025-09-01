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

# Ultra-light in-memory store
_items: Dict[str, memoryview] = {}
_lock = asyncio.Lock()
MAX_PAYLOAD_SIZE = 100 * 1024 * 1024  # 100 MB, kan nog groter
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB chunks → minder async overhead

@app.get("/")
async def root():
    return ORJSONResponse({"message": "Backend is running"})

@app.get("/items")
async def get_items():
    return ORJSONResponse(list(_items.keys()))

@app.post("/items")
async def create_item(request: Request):
    size = 0
    chunks = []

    # stream upload
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_PAYLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Payload too large")
        # direct memoryview → geen kopieën
        chunks.append(memoryview(chunk))

    item_id = str(uuid.uuid4())
    async with _lock:
        # combineer chunks via memoryview → geen extra bytes copy
        total = b"".join(chunks)
        _items[item_id] = memoryview(total)

    return ORJSONResponse({"id": item_id})

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    payload = _items.get(item_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Item not found")

    # StreamingResponse uit memoryview
    def iterator(chunk_size=CHUNK_SIZE):
        mv = payload
        for i in range(0, len(mv), chunk_size):
            yield mv[i:i+chunk_size]

    return StreamingResponse(iterator(), media_type="application/octet-stream")

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    async with _lock:
        if item_id in _items:
            del _items[item_id]
            return ORJSONResponse({"status": "deleted"})
    raise HTTPException(status_code=404, detail="Item not found")
