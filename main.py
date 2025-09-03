import os
from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()
db = {}  # id -> compressed bytes
buffers = {}  # id -> temporary buffer

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    while True:
        msg = await ws.receive_bytes()

        try:
            text = msg.decode()
        except:
            text = None

        # Start new upload
        if text and text.startswith("NEWID:"):
            current_id = text[6:]
            buffers[current_id] = b""
            db[current_id] = b""
            await ws.send_text(f"READY:{current_id}")

        # End upload
        elif text and text.startswith("ENDUPLOAD:"):
            item_id = text[10:]
            if item_id in buffers:
                db[item_id] = buffers[item_id]
                del buffers[item_id]
                await ws.send_text(f"ADDED:{item_id}")

        # GET payload
        elif text and text.startswith("GET:"):
            item_id = text[4:]
            if item_id in db and db[item_id]:
                await ws.send_bytes(db[item_id])
                await ws.send_text(f"{len(db[item_id])} bytes")
                await ws.send_text(f"END:{item_id}")
            else:
                await ws.send_text("ERROR:NOT_FOUND")

        # Payload chunks
        else:
            if current_id:
                buffers[current_id] += msg
