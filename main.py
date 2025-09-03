import zlib
import uuid
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS zodat frontend van andere site kan verbinden
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = {}  # ID -> compressed bytes

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_bytes()
        try:
            # Text commands
            if data.startswith(b"ADD:"):
                payload = data[4:]  # rest is payload
                item_id = str(uuid.uuid4())
                compressed = zlib.compress(payload)  # normal zlib
                db[item_id] = compressed
                await ws.send_text(f"ADDED:{item_id}")

            elif data.startswith(b"GET:"):
                item_id = data[4:].decode()
                if item_id in db:
                    await ws.send_bytes(db[item_id])
                else:
                    await ws.send_text("ERROR:NOT_FOUND")

            elif data.startswith(b"DEL:"):
                item_id = data[4:].decode()
                db.pop(item_id, None)
                await ws.send_text(f"DELETED:{item_id}")

        except Exception as e:
            await ws.send_text(f"ERROR:{e}")
