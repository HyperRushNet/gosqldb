# main.py
import uuid
from fastapi import FastAPI, WebSocket

app = FastAPI()
db = {}  # id -> raw bytes

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_bytes()
        if data.startswith(b"ADD:"):
            payload = data[4:]
            item_id = str(uuid.uuid4())
            db[item_id] = payload  # raw storage, no compression
            await ws.send_text(f"ADDED:{item_id}")
        elif data.startswith(b"GET:"):
            item_id = data[4:].decode()
            if item_id in db:
                await ws.send_bytes(db[item_id])
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
