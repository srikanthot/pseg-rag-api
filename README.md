# RAG Chatbot

Minimal RAG (Retrieval-Augmented Generation) chatbot using Azure AI Search and Azure OpenAI.

- **Backend** — FastAPI, exposes `GET /health` and `POST /chat`
- **UI** — Streamlit, calls the backend and renders answers with source citations

## How to run locally

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your Azure credentials (OpenAI, AI Search, Blob Storage).

### 4. Run the backend

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok"}`

### 5. Run the Streamlit UI

```bash
streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## API

### `GET /health`
```json
{"status": "ok"}
```

### `POST /chat`
Request:
```json
{"question": "What is the maximum load for transformer T1?", "session_id": "optional"}
```
Response:
```json
{
  "answer": "The maximum load is ...",
  "citations": [
    {"title": "Transformer Manual", "url": "https://...", "page": 12}
  ]
}
```

## Project structure

```
backend/app/
  main.py      — FastAPI app (endpoints)
  config.py    — env var loading
  rag.py       — retrieve from Azure AI Search + generate with Azure OpenAI

ui/
  app.py       — Streamlit chat UI

requirements.txt
.env.example
```
