import zlib
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

db={}           # id -> bytes
chunk_db={}     # id -> list of bytes

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        msg=await ws.receive()
        if "text" in msg:
            data=msg["text"]
            import json
            obj=json.loads(data)
            cmd=obj.get("cmd")
            if cmd=="ADD_CHUNK":
                cid=obj["id"]
                index=obj["index"]
                total=obj["total"]
                if cid not in chunk_db:
                    chunk_db[cid]=[None]*total
                # next message should be bytes
                msg2=await ws.receive_bytes()
                chunk_db[cid][index]=msg2
                # if last chunk received, merge and store
                if all(chunk_db[cid]):
                    db[cid]=b"".join(chunk_db[cid])
                    chunk_db.pop(cid)
                    await ws.send_text(f"ADDED:{cid}")
            elif cmd=="GET":
                item_id=obj["id"]
                if item_id in db:
                    await ws.send_bytes(db[item_id])
                else:
                    await ws.send_text("ERROR:NOT_FOUND")
            elif cmd=="DEL":
                db.pop(obj["id"],None)
                await ws.send_text(f"DELETED:{obj['id']}")
