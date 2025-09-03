# main.py
import uuid
from fastapi import FastAPI, WebSocket

app = FastAPI()
db = {}  # id -> bytearray (merged chunks)
pending_chunks = {}  # temp storage per connection for chunked ADD

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    conn_id = str(uuid.uuid4())
    pending_chunks[conn_id] = bytearray()
    while True:
        data = await ws.receive_bytes()
        if data.startswith(b"ADD:"):
            payload = data[4:]
            # append to pending_chunks
            pending_chunks[conn_id].extend(payload)
            # simple logic: if last chunk (or chunk >= 256KB) -> finalize
            if len(payload) < 256*1024:
                item_id = str(uuid.uuid4())
                db[item_id] = bytes(pending_chunks[conn_id])
                pending_chunks[conn_id].clear()
                await ws.send_text(f"ADDED:{item_id}")
        elif data.startswith(b"GET:"):
            item_id = data[4:].decode()
            if item_id in db:
                full_payload = db[item_id]
                chunk_size = 256*1024
                for i in range(0, len(full_payload), chunk_size):
                    await ws.send_bytes(full_payload[i:i+chunk_size])
            else:
                await ws.send_text("ERROR:NOT_FOUND")
        elif data.startswith(b"LIST"):
            await ws.send_text("LIST:" + ",".join(db.keys()))
        elif data.startswith(b"DEL:"):
            item_id = data[4:].decode()
            db.pop(item_id, None)
            await ws.send_text(f"DELETED:{item_id}")
        else:
            await ws.send_text("ERROR:UNKNOWN_COMMAND")
