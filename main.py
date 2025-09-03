import zlib
import uuid
import base64
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend from any origin
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
                payload_b64 = data.get("payload")
                compressed = base64.b64decode(payload_b64)
                db[item_id] = compressed
                await ws.send_text(f"ADDED:{item_id}")

            elif cmd == "GET":
                item_id = data.get("id")
                if item_id in db:
                    # Return as binary
                    await ws.send_bytes(db[item_id])
                else:
                    await ws.send_text("ERROR:NOT_FOUND")

            elif cmd == "DEL":
                item_id = data.get("id")
                db.pop(item_id, None)
                await ws.send_text(f"DELETED:{item_id}")

        except Exception as e:
            await ws.send_text(f"ERROR:{e}")
