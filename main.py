from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging

app = FastAPI()
db = {}  # id -> compressed bytes
logging.basicConfig(level=logging.INFO)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    buffer = b""

    logging.info("Client connected")

    try:
        while True:
            msg = await ws.receive()

            # Binary chunk
            if msg["type"] == "websocket.bytes":
                if current_id is not None:
                    buffer += msg["bytes"]
                    logging.debug(f"Received chunk ({len(msg['bytes'])} bytes) for ID {current_id}")
                continue

            # Text message
            if msg["type"] == "websocket.text":
                text = msg.get("text","")

                # NEWID
                if text.startswith("NEWID:"):
                    current_id = text[6:]
                    buffer = b""
                    db[current_id] = b""
                    logging.info(f"NEWID received: {current_id}")
                    await ws.send_text(f"READY:{current_id}")

                # GET
                elif text.startswith("GET:"):
                    item_id = text[4:]
                    if item_id in db and db[item_id]:
                        await ws.send_bytes(db[item_id])
                        await ws.send_text(f"END:{item_id}")
                        logging.info(f"GET sent for ID {item_id} ({len(db[item_id])} bytes)")
                    else:
                        await ws.send_text("ERROR:NOT_FOUND")
                        logging.warning(f"GET error: ID {item_id} not found")

                # ENDUPLOAD
                elif text.startswith("ENDUPLOAD:"):
                    end_id = text[10:]
                    if end_id == current_id:
                        db[current_id] = buffer
                        await ws.send_text(f"ADDED:{current_id}")
                        logging.info(f"Upload complete for ID {current_id} ({len(buffer)} bytes)")
                        buffer = b""
                    else:
                        await ws.send_text("ERROR:UPLOAD_MISMATCH")
                        logging.warning(f"ENDUPLOAD mismatch: {end_id} vs {current_id}")

                # LIST all IDs
                elif text == "LIST":
                    ids = ",".join(db.keys())
                    await ws.send_text(f"IDS:{ids}")
                    logging.info(f"LIST sent: {ids}")

                # Echo any other text
                else:
                    logging.info(f"Received text: {text}")
                    await ws.send_text(f"ECHO:{text}")

    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: {current_id}")
