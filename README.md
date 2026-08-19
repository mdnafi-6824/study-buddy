# Study Buddy 🧠

A web-based LLM chatbot built for COIT12204 Assessment 2. Study Buddy is a
friendly study assistant with a chat UI, a FastAPI backend, and a
persistent per-session conversation with an LLM.

![architecture](architecture-diagram.svg)

## Features

- Clean, colourful chat interface (HTML/CSS/JS) with message history,
  a "typing…" loading state, and quick-prompt shortcuts.
- FastAPI backend exposing `POST /api/chat`.
- Session-based conversation history kept server-side.
- Basic input sanitisation to reduce prompt-injection risk.
- Configurable system persona ("Study Buddy").
- Works with Anthropic Claude or OpenAI — switch with one env var.
- Dockerised for one-command local deployment.

## Project structure

```
study-buddy/
├── backend/
│   ├── main.py            # FastAPI app, /api/chat, /api/health, /api/reset
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── docker-compose.yml
├── architecture-diagram.svg
└── README.md
```

## 1. Run locally without Docker (fastest for development)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then paste your API key into .env
uvicorn main:app --reload
```

Backend is now on `http://localhost:8000`.

Open `frontend/index.html` directly in your browser (or serve it, e.g.
`python -m http.server 8080` from inside `frontend/`), then visit
`http://localhost:8080`.

## 2. Run with Docker (recommended for the deployment requirement)

```bash
cd study-buddy
cp backend/.env.example backend/.env   # add your API key
docker compose up --build
```

- Front-end: http://localhost:8080
- Backend API: http://localhost:8000/api/health

Stop with `docker compose down`.

## 3. Configuration

Set these in `backend/.env`:

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `anthropic` (default) or `openai` |
| `ANTHROPIC_API_KEY` | Required if using Anthropic |
| `OPENAI_API_KEY` | Required if using OpenAI |
| `MODEL_NAME` | Model id, e.g. `claude-sonnet-4-6` or `gpt-4o-mini` |

## 4. Design decisions

- **FastAPI** was chosen for its async support, automatic OpenAPI docs,
  and Pydantic validation, which made request/response typing and
  input-length limits straightforward to enforce.
- **Server-side, session-based history** (keyed by a `session_id` the
  client stores in `localStorage`) keeps conversation state out of the
  browser so the system prompt and full context can't be tampered with
  client-side.
- **Basic sanitisation** strips control characters, caps message length,
  and neutralises role-spoofing strings (e.g. `"system:"`,
  `"### instruction"`) before a message is added to the conversation —
  a lightweight but real mitigation appropriate for the assessment scope.
- **Provider abstraction**: `call_llm()` dispatches to Anthropic or
  OpenAI based on one env var, so the grader can test with whichever key
  is available without touching the front-end.
- **Docker Compose** runs the API and a static Nginx front-end as two
  containers, matching the "front-end → back-end → LLM API" architecture
  in one command.

## 5. AI usage statement

This project was built with the assistance of Claude (Anthropic), used to:
- scaffold the FastAPI backend structure and the sanitisation logic,
- design and implement the front-end chat UI and styling,
- write the Docker/Compose configuration and this README,
- draft the accompanying technical report for editing and review.

All AI-assisted code was reviewed and tested locally before submission.
