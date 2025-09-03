import uuid
from fastapi import FastAPI, WebSocket

app = FastAPI()
db = {}  # ID -> Base64 string

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        msg = await ws.receive_text()  # altijd text
        if msg.startswith("ADD:"):
            payload = msg[4:]  # Base64 LZ string
            item_id = str(uuid.uuid4())
            db[item_id] = payload
            await ws.send_text(f"ADDED:{item_id}")
        elif msg.startswith("GET:"):
            item_id = msg[4:]
            if item_id in db:
                await ws.send_text(db[item_id])
            else:
                await ws.send_text("ERROR:NOT_FOUND")
        elif msg.startswith("DEL:"):
            item_id = msg[4:]
            db.pop(item_id, None)
            await ws.send_text(f"DELETED:{item_id}")
