"""Custom FastAPI + DevNext-Themed UI Server powered by Google ADK + RAG."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv, set_key
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

from devnext_agent.agent import DEFAULT_MODEL, build_agent  # noqa: E402
from devnext_agent.rag import LAST_RETRIEVED_SOURCES, rag_engine  # noqa: E402

APP_NAME = "devnext_2026_rag_app"

app = FastAPI(
    title="ET TechGig DevNext '26 — Google ADK + RAG Concierge",
    description="Custom DevNext-themed UI backed by Google ADK Runner, InMemorySessionService, and Hybrid Gemini RAG.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Global ADK SessionService & Runner (initialized once, refreshed only if model/key changes)
session_service = InMemorySessionService()
current_agent = build_agent()
runner = Runner(
    app_name=APP_NAME,
    agent=current_agent,
    session_service=session_service,
    auto_create_session=True,
)


def _is_api_configured() -> bool:
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    if key and key != "your_gemini_api_key_here":
        return True
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"true", "1"}:
        return True
    return False


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    user_id: str = "devnext_attendee"


class KeyConfigRequest(BaseModel):
    api_key: str = Field(..., min_length=10)


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/assets/logo.png")
async def serve_logo() -> FileResponse:
    logo_path = BASE_DIR / "image.png"
    if not logo_path.exists():
        raise HTTPException(status_code=404, detail="Logo image.png not found.")
    return FileResponse(path=str(logo_path), media_type="image/png")


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    return {
        "event": "ET TechGig DevNext '26",
        "official_url": "https://techgig.com/devnext",
        "model": os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
        "api_key_configured": _is_api_configured(),
        "embeddings_ready": rag_engine.embeddings is not None,
        "rag_chunks": len(rag_engine.chunks),
        "sections": [
            {"chunk_id": c.chunk_id, "section": c.section, "source_file": c.source_file}
            for c in rag_engine.chunks
        ],
    }


@app.post("/api/configure-key")
async def configure_api_key(req: KeyConfigRequest) -> dict[str, Any]:
    global current_agent, runner

    cleaned_key = req.api_key.strip()
    os.environ["GOOGLE_API_KEY"] = cleaned_key
    try:
        if not ENV_FILE.exists():
            ENV_FILE.write_text("", encoding="utf-8")
        set_key(str(ENV_FILE), "GOOGLE_API_KEY", cleaned_key)
    except OSError:
        # Serverless / read-only filesystem: keep key in process environment
        pass

    # Build dense Gemini embeddings now that GOOGLE_API_KEY is available
    rag_engine.reload()

    # Rebuild ADK Agent & Runner bound to the active environment
    current_agent = build_agent()
    runner = Runner(
        app_name=APP_NAME,
        agent=current_agent,
        session_service=session_service,
        auto_create_session=True,
    )

    return {
        "ok": True,
        "embeddings_ready": rag_engine.embeddings is not None,
        "rag_chunks": len(rag_engine.chunks),
    }


@app.post("/api/chat")
async def chat_with_agent(req: ChatRequest) -> dict[str, Any]:
    if not _is_api_configured():
        raise HTTPException(
            status_code=400,
            detail=(
                "GOOGLE_API_KEY is not configured yet. Add GOOGLE_API_KEY to .env "
                "or click 'Configure Key' in the top bar."
            ),
        )

    session_id = req.session_id or f"devnext_{uuid.uuid4().hex[:10]}"
    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=req.message.strip())],
    )

    # Reset per-turn retrieved RAG citations tracker (mutable list shared across child contexts)
    turn_sources: list[dict[str, Any]] = []
    token = LAST_RETRIEVED_SOURCES.set(turn_sources)

    try:
        final_chunks: list[str] = []
        fallback_chunks: list[str] = []

        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=session_id,
            new_message=user_message,
        ):
            if event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
                if text_parts:
                    joined = "".join(text_parts)
                    if event.is_final_response():
                        final_chunks.append(joined)
                    else:
                        fallback_chunks.append(joined)

        answer = "".join(final_chunks).strip() or "".join(fallback_chunks).strip()
        if not answer:
            answer = (
                "I couldn't generate a response for that query. Please ask a question "
                "related to **ET TechGig DevNext '26**."
            )

        return {
            "session_id": session_id,
            "response": answer,
            "sources": turn_sources,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ADK execution error: {exc}") from exc
    finally:
        LAST_RETRIEVED_SOURCES.reset(token)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("app:app", host=host, port=port, reload=False)

