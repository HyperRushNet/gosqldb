import zlib
import uuid
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

db = {}  # id -> compressed bytes

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_bytes()
        # NEW ID
        if data.startswith(b"NEWID:"):
            item_id = data[6:].decode()
            db[item_id] = b""  # init empty
            await ws.send_text(f"READY:{item_id}")
        # ADD chunk
        elif data.startswith(b"CHUNK:"):
            # not needed in this backend, frontend sends raw bytes
            pass
        # GET
        elif data.startswith(b"GET:"):
            item_id = data[4:].decode()
            if item_id in db:
                payload = db[item_id]
                await ws.send_bytes(payload)
                await ws.send_text(f"END:{item_id}")
            else:
                await ws.send_text("ERROR:NOT_FOUND")
        # ADD final payload
        else:
            # treat all other bytes as full payload
            if hasattr(ws, "current_id"):
                db[ws.current_id] = data
            else:
                # fallback id
                new_id = str(uuid.uuid4())
                db[new_id] = data
                ws.current_id = new_id
                await ws.send_text(f"ADDED:{new_id}")
