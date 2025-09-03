import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

db={} # id -> bytes buffer

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        msg=await ws.receive()
        # Binary chunk
        if "bytes" in msg:
            if "current_id" in ws.__dict__:
                db[ws.current_id]+=msg["bytes"]
        elif "text" in msg:
            import json
            data=json.loads(msg["text"])
            if "cmd" in data:
                cmd=data["cmd"]
                item_id=data.get("id")
                if cmd=="GET":
                    if item_id in db:
                        await ws.send_bytes(db[item_id])
                    else:
                        await ws.send_text("ERROR:NOT_FOUND")
                elif cmd=="DEL":
                    db.pop(item_id,None)
                    await ws.send_text(f"DELETED:{item_id}")
            else:
                # initial chunk header
                ws.current_id=data["id"]
                db[ws.current_id]=b""
