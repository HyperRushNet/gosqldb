from fastapi import FastAPI, WebSocket

app = FastAPI()
db = {}  # id -> compressed bytes

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    buffer = b""  # temporary buffer for chunks

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
            buffer = b""
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

        # Payload chunk
        else:
            if current_id:
                buffer += msg  # accumulate all chunks
                # Only set db[current_id] once all chunks are sent
                # Here we assume the client will send a final "ENDUPLOAD" text message
            # optional: handle end of upload
