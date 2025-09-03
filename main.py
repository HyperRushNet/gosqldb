import uuid
from fastapi import FastAPI, WebSocket
import asyncio

app = FastAPI()

db = {}  # ID -> bytearray

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    db[current_id] = bytearray()
    try:
        while True:
            msg = await ws.receive_bytes()
            # Detect begin of new item
            if msg.startswith(b"NEWID:"):
                current_id = msg[6:].decode()
                db[current_id] = bytearray()
                await ws.send_text(f"READY:{current_id}")
                continue
            # Detect GET request
            if msg.startswith(b"GET:"):
                item_id = msg[4:].decode()
                if item_id not in db:
                    await ws.send_text("ERROR:NOT_FOUND")
                    continue
                full = db[item_id]
                chunk_size = 256*1024
                for i in range(0,len(full),chunk_size):
                    await ws.send_bytes(full[i:i+chunk_size])
                await ws.send_text(f"END:{item_id}")
                continue
            # Otherwise treat as chunk of bytes
            if current_id:
                db[current_id] += msg
                await ws.send_text(f"CHUNK:{len(msg)}")
    except Exception as e:
        await ws.close()
