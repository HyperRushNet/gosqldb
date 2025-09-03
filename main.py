import asyncio, json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

db={} # id -> bytes

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ws.current_id=None
    while True:
        msg = await ws.receive()
        if "bytes" in msg:
            if ws.current_id:
                db[ws.current_id]+=msg["bytes"]
        elif "text" in msg:
            data=json.loads(msg["text"])
            if "cmd" in data:
                cmd=data["cmd"]
                item_id=data.get("id")
                if cmd=="GET":
                    if item_id in db:
                        full=db[item_id]
                        chunk_size=256*1024
                        for i in range(0,len(full),chunk_size):
                            await ws.send_bytes(full[i:i+chunk_size])
                        await ws.send_text(f"END:{item_id}")
                    else:
                        await ws.send_text("ERROR:NOT_FOUND")
                elif cmd=="DEL":
                    db.pop(item_id,None)
                    await ws.send_text(f"DELETED:{item_id}")
            elif "id" in data:
                ws.current_id=data["id"]
                db[ws.current_id]=b""
