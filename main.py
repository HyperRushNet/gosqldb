import zlib
import uuid
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

db = {}  # ID -> compressed bytes

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_bytes()  # krijg binaire data
        if data.startswith(b"ADD:"):
            payload = data[4:]
            item_id = str(uuid.uuid4())
            compressed = zlib.compress(payload)
            db[item_id] = compressed
            await ws.send_text(f"ADDED:{item_id}")
        elif data.startswith(b"GET:"):
            item_id = data[4:].decode()
            if item_id in db:
                await ws.send_bytes(db[item_id])  # stuur binaire data terug
            else:
                await ws.send_text("ERROR:NOT_FOUND")
        elif data.startswith(b"LIST"):
            ids = ",".join(db.keys())
            await ws.send_text(f"LIST:{ids}")
        elif data.startswith(b"DEL:"):
            item_id = data[4:].decode()
            db.pop(item_id, None)
            await ws.send_text(f"DELETED:{item_id}")
