import zlib
import uuid
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS voor frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = {}  # id -> bytes

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    while True:
        try:
            msg = await ws.receive()
            if "text" in msg:
                import json
                data = json.loads(msg["text"])
                cmd = data.get("cmd")
                if cmd == "ADD":
                    current_id = data.get("id") or str(uuid.uuid4())
                    db[current_id] = b''  # placeholder
                    await ws.send_text(f"READY:{current_id}")
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
            elif "bytes" in msg:
                if current_id:
                    db[current_id] = msg["bytes"]
                    await ws.send_text(f"ADDED:{current_id}")
                    current_id = None
        except Exception as e:
            await ws.send_text(f"ERROR:{e}")
