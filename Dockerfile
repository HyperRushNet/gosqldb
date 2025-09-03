FROM python:3.11-slim

# Werkdirectory instellen
WORKDIR /app

# Code en requirements kopiëren
COPY . .

# Dependencies installeren
RUN pip install --no-cache-dir -r requirements.txt

# Uvicorn starten met de juiste poort van Render
# Let op: altijd $PORT gebruiken en maar 1 worker voor WebSockets
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
