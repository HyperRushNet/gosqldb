from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
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
items = {}

@app.get("/")
def read_root():
    return {"message": "Backend is running"}

# ✅ Alle items ophalen
@app.get("/items")
def get_items():
    return list(items.values())

# ✅ Nieuw item toevoegen (met tekst + foto)
@app.post("/items")
async def create_item(
    name: str = Form(...),
    photo: Optional[str] = Form(None)
):
    item_id = str(uuid.uuid4())
    items[item_id] = {
        "id": item_id,
        "name": name,
        "photo": photo  # Base64 string of None
    }
    return items[item_id]   # ⬅️ altijd volledig object terug

# ✅ Item verwijderen
@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    if item_id in items:
        del items[item_id]
        return {"status": "deleted"}
    return {"error": "Item not found"}
