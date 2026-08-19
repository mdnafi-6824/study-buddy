"""
Study Buddy - Backend API
COIT12204 Assessment 2

A small FastAPI service that exposes /api/chat, keeps per-session
conversation history in memory, applies basic input sanitisation to
reduce prompt-injection risk, and forwards the conversation to an
LLM provider (Anthropic Claude by default).
"""

import os
import re
import uuid
import time
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
load_dotenv()
# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # "anthropic" or "openai"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-6")

SYSTEM_PERSONA = (
    "You are Study Buddy, a friendly, encouraging study assistant for "
    "university students. You explain concepts clearly, break down "
    "problems into steps, suggest practice questions, and keep a "
    "supportive, upbeat tone. Keep answers focused and not overly long "
    "unless the student asks for detail. "
    "Do not use markdown formatting: no **bold**, no # headers, no "
    "markdown bullet dashes. The chat interface displays plain text, so "
    "write in plain sentences and paragraphs. If you need to list "
    "things, use short numbered lines like '1) ...' on separate lines "
    "instead of markdown lists."
)

MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_MESSAGES = 20  # trim context so it doesn't grow forever

app = FastAPI(title="Study Buddy API")

# Allow the front-end (served separately or via file://) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# In-memory conversation store: { session_id: [ {role, content}, ... ] }
# For a real deployment this would be Redis / a database. In-memory is
# sufficient to demonstrate session-based conversation state for this
# assessment and keeps the deployment story simple (no extra services).
# --------------------------------------------------------------------------

conversations: Dict[str, List[dict]] = {}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


# --------------------------------------------------------------------------
# Basic sanitisation to reduce prompt-injection risk.
# This is intentionally simple (assessment scope), not a production-grade
# defence. It strips control characters, caps length, and neutralises
# attempts to spoof role markers or "ignore previous instructions" style
# payloads before the text is placed into the user turn.
# --------------------------------------------------------------------------

_ROLE_SPOOF_PATTERN = re.compile(
    r"(system\s*:|assistant\s*:|^\s*###\s*(system|instruction))",
    re.IGNORECASE,
)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitise(text: str) -> str:
    text = text.strip()[:MAX_MESSAGE_LENGTH]
    text = _CONTROL_CHARS.sub("", text)
    # Neutralise attempts to impersonate a role marker rather than deleting
    # the user's words outright, so legitimate messages still make sense.
    text = _ROLE_SPOOF_PATTERN.sub("[filtered]", text)
    return text


# --------------------------------------------------------------------------
# LLM call
# --------------------------------------------------------------------------

def call_llm(history: List[dict]) -> str:
    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(history)
    elif LLM_PROVIDER == "openai":
        return _call_openai(history)
    raise HTTPException(status_code=500, detail=f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'")


def _call_anthropic(history: List[dict]) -> str:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not set on the server.",
        )
    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic package not installed.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=800,
            system=SYSTEM_PERSONA,
            messages=[{"role": m["role"], "content": m["content"]} for m in history],
        )
        return "".join(block.text for block in response.content if block.type == "text")
    except Exception as exc:  # network/auth/rate-limit errors, etc.
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}")


def _call_openai(history: List[dict]) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set on the server.",
        )
    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(status_code=500, detail="openai package not installed.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    messages = [{"role": "system", "content": SYSTEM_PERSONA}] + [
        {"role": m["role"], "content": m["content"]} for m in history
    ]
    try:
        response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
        return response.choices[0].message.content
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "provider": LLM_PROVIDER, "model": MODEL_NAME}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    clean_message = sanitise(req.message)

    history = conversations.setdefault(session_id, [])
    history.append({"role": "user", "content": clean_message})

    # Keep the context window bounded.
    trimmed = history[-MAX_HISTORY_MESSAGES:]

    reply_text = call_llm(trimmed)

    history.append({"role": "assistant", "content": reply_text})
    conversations[session_id] = history

    return ChatResponse(reply=reply_text, session_id=session_id)


@app.post("/api/reset")
def reset(session_id: str):
    conversations.pop(session_id, None)
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
