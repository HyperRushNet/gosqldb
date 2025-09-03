import os
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

app = FastAPI()
db = {}  # id -> compressed bytes

# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    buffer = b""

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

        # ENDUPLOAD
        elif text and text.startswith("ENDUPLOAD:"):
            end_id = text[10:]
            if end_id == current_id:
                db[current_id] = buffer
                await ws.send_text(f"ADDED:{current_id}")
                buffer = b""
            else:
                await ws.send_text("ERROR:UPLOAD_MISMATCH")

        # Payload chunk
        else:
            if current_id:
                buffer += msg

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
