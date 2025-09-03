import zlib
from fastapi import FastAPI, WebSocket

app = FastAPI()
db = {}  # id -> compressed bytes

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    while True:
        try:
            msg = await ws.receive_bytes()
        except:
            continue

        try:
            text = msg.decode()
        except:
            text = None

        # NEW ID
        if text and text.startswith("NEWID:"):
            current_id = text[6:]
            db[current_id] = b""
            await ws.send_text(f"READY:{current_id}")

        # GET
        elif text and text.startswith("GET:"):
            item_id = text[4:]
            if item_id in db and db[item_id]:
                await ws.send_bytes(db[item_id])
                await ws.send_text(f"END:{item_id}")
            else:
                await ws.send_text("ERROR:NOT_FOUND")

        # Payload
        else:
            if current_id:
                # append if multiple chunks, else store single payload
                db[current_id] += msg
                await ws.send_text(f"ADDED:{current_id}")
