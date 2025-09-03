from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging

app = FastAPI()
db = {}  # id -> compressed bytes

logging.basicConfig(level=logging.INFO)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    current_id = None
    buffer = b""

    logging.info("Client connected")

    try:
        while True:
            try:
                msg = await ws.receive()
            except Exception as e:
                logging.error(f"Error receiving message: {e}")
                continue

            if msg["type"] == "websocket.disconnect":
                logging.info(f"Client disconnected: {current_id}")
                break

            # Binary data chunk
            if msg["type"] == "websocket.bytes":
                if current_id is not None:
                    buffer += msg["bytes"]
                    logging.debug(f"Received binary chunk ({len(msg['bytes'])} bytes) for ID {current_id}")
                continue

            # Text data
            if msg["type"] == "websocket.text":
                text = msg.get("text", "")
                if text.startswith("NEWID:"):
                    current_id = text[6:]
                    buffer = b""
                    logging.info(f"NEWID received: {current_id}")
                    await ws.send_text(f"READY:{current_id}")

                elif text.startswith("GET:"):
                    item_id = text[4:]
                    if item_id in db and db[item_id]:
                        await ws.send_bytes(db[item_id])
                        await ws.send_text(f"END:{item_id}")
                        logging.info(f"GET sent for ID: {item_id} ({len(db[item_id])} bytes)")
                    else:
                        await ws.send_text("ERROR:NOT_FOUND")
                        logging.warning(f"GET error: ID {item_id} not found")

                elif text.startswith("ENDUPLOAD:"):
                    end_id = text[10:]
                    if end_id == current_id:
                        db[current_id] = buffer
                        await ws.send_text(f"ADDED:{current_id}")
                        logging.info(f"Upload complete for ID: {current_id} ({len(buffer)} bytes)")
                        buffer = b""
                    else:
                        await ws.send_text("ERROR:UPLOAD_MISMATCH")
                        logging.warning(f"ENDUPLOAD mismatch: {end_id} vs {current_id}")

                else:
                    # Optional: handle arbitrary text messages
                    logging.info(f"Received text message: {text}")
                    await ws.send_text(f"ECHO:{text}")

    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: {current_id}")
