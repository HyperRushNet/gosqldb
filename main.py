import zlib
import uuid
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = {}  # id -> compressed bytes

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        try:
            msg = await ws.receive_text()
            import json
            data = json.loads(msg)

            cmd = data.get("cmd")
            if cmd == "ADD":
                item_id = data.get("id") or str(uuid.uuid4())
                payload = bytes(data.get("payload"), 'latin1')  # receive raw binary as latin1 string
                db[item_id] = payload
                await ws.send_text(f"ADDED:{item_id}")

            elif cmd == "GET":
                item_id = data.get("id")
                if item_id in db:
                    await ws.send_bytes(db[item_id])
                else:
                    await ws.send_text("ERROR:NOT_FOUND")

            elif cmd == "DEL":
                item_id = data.get("id")
                db.pop(item_id, None)
                await ws.send_text(f"DELETED:{item_id}")

        except Exception as e:
            await ws.send_text(f"ERROR:{e}")
