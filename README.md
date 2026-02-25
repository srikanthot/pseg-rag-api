# PSEG RAG Chatbot

Retrieval-Augmented Generation chatbot for PSEG technical manuals.
Uses Azure AI Search (hybrid vector search) and Azure OpenAI to answer questions from indexed PDF documents.

- **Backend** — FastAPI (`GET /health`, `POST /chat`)
- **UI** — Streamlit chat interface with source citations

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your Azure credentials. See `.env.example` for all required variables.

### 3. Run the backend

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok"}`

### 4. Run the UI

```bash
python -m streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## API

### `GET /health`

```json
{"status": "ok"}
```

### `POST /chat`

**Request:**
```json
{
  "question": "What are the gas pressure limits for residential service?",
  "chat_history": [
    {"role": "user", "content": "previous question"},
    {"role": "assistant", "content": "previous answer"}
  ],
  "top_k": 5
}
```

`chat_history` and `top_k` are optional.

**Response:**
```json
{
  "answer": "The operating pressure for residential gas service is ...",
  "citations": [
    {"title": "Gas Service Manual", "url": "https://...", "page": 14}
  ]
}
```

---

## Required environment variables

| Variable | Description |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Chat model deployment name (e.g. `gpt-4o-mini`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model deployment name |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | Azure AI Search API key |
| `AZURE_SEARCH_INDEX_NAME` | Name of the existing search index |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob storage connection string (for SAS citation links) |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container holding the PDFs |

---

## Project structure

```
backend/app/
  main.py      — FastAPI endpoints
  config.py    — environment variable loading
  rag.py       — retrieval + generation logic

ui/
  app.py       — Streamlit chat UI

requirements.txt
.env.example
```
