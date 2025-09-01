import uuid
import asyncio
from typing import Dict
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, StreamingResponse
import aiofiles
import os
import tempfile

app = FastAPI()

# CORS open
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# item_id -> file path
_items: Dict[str, str] = {}
_lock = asyncio.Lock()  # protect writes only
MAX_PAYLOAD_SIZE = 50 * 1024 * 1024  # 50MB, kan groter

@app.get("/")
async def root():
    return ORJSONResponse({"message": "Backend is running"})

@app.get("/ping", status_code=204)
async def ping():
    return ORJSONResponse(status_code=204)

@app.get("/items")
async def get_items():
    return ORJSONResponse(list(_items.keys()))

@app.post("/items")
async def create_item(request: Request):
    size = 0
    # Maak een tijdelijk bestand aan voor deze upload
    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    tmp_path = tmp_file.name
    tmp_file.close()  # aiofiles opent zelf

    # Async schrijf in chunks
    async with aiofiles.open(tmp_path, 'wb') as f:
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_PAYLOAD_SIZE:
                raise HTTPException(status_code=413, detail="Payload too large")
            await f.write(chunk)

    item_id = str(uuid.uuid4())
    async with _lock:
        _items[item_id] = tmp_path

    return ORJSONResponse({"id": item_id})

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    path = _items.get(item_id)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Item not found")

    # Async file streaming
    async def file_iterator(file_path, chunk_size=64*1024):
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(file_iterator(path), media_type="application/octet-stream")

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    async with _lock:
        path = _items.pop(item_id, None)

    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
        return ORJSONResponse({"status": "deleted"})

    raise HTTPException(status_code=404, detail="Item not found")
