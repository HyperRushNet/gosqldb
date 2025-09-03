import uuid
from fastapi import FastAPI, WebSocket
import zlib

app = FastAPI()

# opslag: ID -> compressed bytes
db = {}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    current_add_id = None
    buffer = bytearray()
    while True:
        data = await ws.receive()
        # binaire data
        if "bytes" in data:
            if current_add_id:
                buffer.extend(data["bytes"])
                db[current_add_id] = bytes(buffer)
                await ws.send_text(f"ADDED:{current_add_id}")
                current_add_id = None
                buffer = bytearray()
            continue

        # tekst data
        if "text" in data:
            text = data["text"]
            if text.startswith("ADD:"):
                # format ADD:<client_id>:
                parts = text.split(":",2)
                if len(parts) < 3:
                    await ws.send_text("ERROR:INVALID_ADD")
                    continue
                current_add_id = parts[1]
                buffer = bytearray()
            elif text.startswith("GET:"):
                item_id = text[4:]
                if item_id in db:
                    await ws.send_bytes(db[item_id])
                else:
                    await ws.send_text("ERROR:NOT_FOUND")
            elif text.startswith("DEL:"):
                item_id = text[4:]
                db.pop(item_id,None)
                await ws.send_text(f"DELETED:{item_id}")
            elif text.startswith("LIST"):
                ids = ",".join(db.keys())
                await ws.send_text(f"LIST:{ids}")
