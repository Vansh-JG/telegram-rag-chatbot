# Telegram RAG Chatbot

A full-stack app for searching your Telegram history with grounded retrieval, uploading PDFs for document Q&A, and drafting Telegram replies with context before sending them.

## Features

- Sync Telegram chats into a searchable retrieval index
- Ask grounded questions about Telegram conversations
- Select a contact, draft a message, refine it with conversation context, and send it after confirmation
- Upload PDFs and ask questions strictly based on uploaded document content
- FastAPI backend with a Next.js frontend

## Stack

### Backend

- FastAPI
- OpenAI API
- Weaviate Cloud
- Telethon
- PyMuPDF

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4

## Project Structure

```text
telegram-rag-chatbot/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── db/
│   │   ├── schemas/
│   │   └── services/
│   ├── .env
│   ├── .venv/
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── .env.local
│   └── package.json
└── storage/
```

## Requirements

- Python 3.11+ recommended
- Node.js 20+ recommended
- An OpenAI API key
- A Weaviate Cloud cluster URL and API key
- Telegram API credentials if you want Telegram sync and sending

## Environment Variables

### Backend

Create `backend/.env` with:

```env
OPENAI_API_KEY=your_openai_api_key
WEAVIATE_URL=your_weaviate_cluster_url
WEAVIATE_API_KEY=your_weaviate_api_key
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash
TELEGRAM_PHONE=your_telegram_phone_number
TELEGRAM_SESSION_NAME=telegram_session
```

Notes:

- `TELEGRAM_*` values are required for Telegram sync and Telegram sending.
- The backend expects an authorized Telegram session file in `storage/` before ingesting chats or sending messages.

### Frontend

`frontend/.env.local` is optional.

By default, the frontend already uses `http://localhost:8000` if no env var is set.

Create `frontend/.env.local` only if you want to override the backend URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Run Locally

Start the backend:

```bash
cd /Users/vanshgandhi/GitHub/telegram-rag-chatbot/backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Start the frontend in a second terminal:

```bash
cd /Users/vanshgandhi/GitHub/telegram-rag-chatbot/frontend
npm run dev
```

Open:

- Frontend: `http://localhost:3000`
- Backend health check: `http://localhost:8000/health`

## Main Workflows

### Telegram RAG

1. Start both servers.
2. Open the frontend.
3. Click `Sync Telegram` to ingest Telegram chats.
4. Ask grounded questions in the Telegram Q&A panel.

Important:

- Query results come from the latest indexed Telegram data, not live Telegram state.
- If new messages arrive, run `Sync Telegram` again to refresh the index.

### Telegram Compose and Send

1. Select a contact from the contact list or recipient dropdown.
2. Write a rough message in the compose panel.
3. Click `Refine Draft`.
4. Review and edit the refined message.
5. Click `Looks Good, Send`.

### Document Q&A

Use the backend endpoint `POST /documents/upload` to upload PDFs, then ask grounded questions with `POST /chat`.

## API Endpoints

### General

- `GET /` basic backend test route
- `GET /health` health check

### Documents

- `POST /documents/upload` upload and index a PDF
- `POST /chat` ask a grounded question about uploaded documents

### Telegram

- `POST /telegram/ingest` ingest Telegram chats into the retrieval index
- `GET /telegram/contacts` list indexed Telegram contacts
- `POST /telegram/chat` ask a grounded question about Telegram conversations
- `POST /telegram/draft` generate a refined draft for a selected contact
- `POST /telegram/send` send an approved Telegram message

## Readiness Notes

The app is ready for local use with the current setup. Before using Telegram features, make sure:

- `backend/.env` is filled in correctly
- your Telegram session is authorized locally
- your Weaviate cluster is reachable
- your OpenAI API key has access to embeddings and chat completions

## Verification

The following checks passed locally during the final pass:

- `npm run lint` in `frontend/`
- `python -m compileall app` in `backend/`

## Known Behavior

- Telegram Q&A prefers semantically relevant chunks with a recency boost, rather than simply returning the newest messages in chronological order.
- Telegram retrieval uses indexed history from the last sync.
- The frontend dev script uses `next dev --webpack` to avoid the Tailwind resolution issue seen with Turbopack in this repo layout.
