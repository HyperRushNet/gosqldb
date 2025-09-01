from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import uuid

app = FastAPI()

# ✅ CORS op alles toestaan
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simpele in-memory opslag (reset bij server restart)
items = {}  # { id: payload }

@app.get("/")
def read_root():
    return {"message": "Backend is running"}

# ✅ Healthcheck: 204 No Content
@app.get("/ping", status_code=204)
def ping():
    return Response(status_code=204)

# ✅ Alle items ophalen → alleen IDs
@app.get("/items")
def get_items():
    return list(items.keys())

# ✅ Nieuw item toevoegen (alleen tekst → "payload")
@app.post("/items")
async def create_item(payload: str = Form(...)):
    item_id = str(uuid.uuid4())
    items[item_id] = payload
    return {"id": item_id, "payload": payload}

# ✅ Enkel de payload ophalen voor 1 item
@app.get("/items/{item_id}")
def get_item(item_id: str):
    if item_id in items:
        return items[item_id]  # geeft alleen de payload-string terug
    return {"error": "Item not found"}

# ✅ Item verwijderen
@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    if item_id in items:
        del items[item_id]
        return {"status": "deleted"}
    return {"error": "Item not found"}
