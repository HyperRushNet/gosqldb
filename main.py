# main.py
import zlib
import uuid
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

app = FastAPI()

# in-memory DB: id -> compressed bytes (raw deflate)
db: Dict[str, bytes] = {}

def compress_raw_deflate(data: bytes, level: int = 9) -> bytes:
    cobj = zlib.compressobj(level, zlib.DEFLATED, -15)
    return cobj.compress(data) + cobj.flush()

def decompress_raw_deflate(data: bytes) -> bytes:
    dobj = zlib.decompressobj(-15)
    return dobj.decompress(data) + dobj.flush()

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "WS compress server: use websocket on /ws"

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_bytes()
            if msg.startswith(b"ADD:"):
                payload = msg[4:]
                item_id = str(uuid.uuid4())
                compressed = compress_raw_deflate(payload, level=9)
                db[item_id] = compressed
                await ws.send_text(f"ADDED:{item_id}")
            elif msg.startswith(b"GET:"):
                item_id = msg[4:].decode('utf-8')
                compressed = db.get(item_id)
                if compressed is None:
                    await ws.send_text("ERROR:NOT_FOUND")
                else:
                    await ws.send_bytes(compressed)
            elif msg.startswith(b"LIST"):
                ids = ",".join(db.keys())
                await ws.send_text(f"LIST:{ids}")
            elif msg.startswith(b"DEL:"):
                item_id = msg[4:].decode('utf-8')
                db.pop(item_id, None)
                await ws.send_text(f"DELETED:{item_id}")
            else:
                await ws.send_text("ERROR:UNKNOWN_COMMAND")
    except WebSocketDisconnect:
        return

# Run with: uvicorn main:app --host 0.0.0.0 --port 8000
