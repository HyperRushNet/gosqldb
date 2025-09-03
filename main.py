import zlib, asyncio
from fastapi import FastAPI, WebSocket

app = FastAPI()
db = {}  # id -> compressed bytes

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    buffer = bytearray()
    while True:
        data = await ws.receive()
        if "text" in data:
            text = data["text"]
            if text.startswith("ADD:"):
                current_id = text.split(":",2)[1]
                buffer = bytearray()
            elif text.startswith("GET:"):
                item_id = text[4:]
                if item_id in db:
                    chunk_size = 256*1024
                    for i in range(0,len(db[item_id]),chunk_size):
                        await ws.send_bytes(db[item_id][i:i+chunk_size])
                        await asyncio.sleep(0)  # yield
                else:
                    await ws.send_text("ERROR:NOT_FOUND")
            elif text.startswith("DEL:"):
                db.pop(text[4:],None)
                await ws.send_text(f"DELETED:{text[4:]}")
        elif "bytes" in data:
            if current_id:
                buffer.extend(data["bytes"])
                db[current_id]=bytes(buffer)
                await ws.send_text(f"ADDED:{current_id}")
                current_id=None
                buffer=bytearray()
