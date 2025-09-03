# main.py
import uuid
from fastapi import FastAPI, WebSocket

app = FastAPI()
db = {}  # id -> bytes

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    pending_chunks = bytearray()
    while True:
        data = await ws.receive_bytes()
        if data.startswith(b"ADD:"):
            payload = data[4:]
            pending_chunks.extend(payload)
            # detect end of chunked ADD: last chunk < 256 KB or Base16 flag
            if len(payload) < 256*1024:
                item_id = str(uuid.uuid4())
                db[item_id] = bytes(pending_chunks)
                pending_chunks.clear()
                await ws.send_text(f"ADDED:{item_id}")
        elif data.startswith(b"GET:"):
            item_id = data[4:].decode()
            if item_id in db:
                payload = db[item_id]
                chunk_size = 256*1024
                for i in range(0, len(payload), chunk_size):
                    await ws.send_bytes(payload[i:i+chunk_size])
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
