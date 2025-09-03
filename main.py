import zlib
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

db={} # id -> raw deflate bytes

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        msg=await ws.receive()
        if "text" in msg:
            import json
            data=json.loads(msg["text"])
            cmd=data.get("cmd")
            item_id=data.get("id")
            if cmd=="ADD":
                payload_msg=await ws.receive_bytes()
                db[item_id]=payload_msg
                await ws.send_text(f"ADDED:{item_id}")
            elif cmd=="GET":
                if item_id in db:
                    await ws.send_bytes(db[item_id])
                else:
                    await ws.send_text("ERROR:NOT_FOUND")
            elif cmd=="DEL":
                db.pop(item_id,None)
                await ws.send_text(f"DELETED:{item_id}")
