from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import json

app = FastAPI()

# Static files (zodat index.html direct werkt op Render)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# In-memory database
db = {}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg["action"] == "list":
                await ws.send_text(json.dumps({"action": "list", "ids": list(db.keys())}))

            elif msg["action"] == "get":
                item_id = msg["id"]
                if item_id in db:
                    await ws.send_text(json.dumps({
                        "action": "get",
                        "id": item_id,
                        "data": db[item_id]
                    }))
                else:
                    await ws.send_text(json.dumps({"error": f"Item {item_id} not found"}))

            elif msg["action"] == "add":
                new_id = str(len(db) + 1)
                db[new_id] = msg["data"]
                await ws.send_text(json.dumps({"action": "add", "id": new_id}))

            elif msg["action"] == "delete":
                item_id = msg["id"]
                if item_id in db:
                    del db[item_id]
                    await ws.send_text(json.dumps({"action": "delete", "id": item_id}))
                else:
                    await ws.send_text(json.dumps({"error": f"Item {item_id} not found"}))

    except WebSocketDisconnect:
        print("Client disconnected")
