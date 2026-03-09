"""API routes for the Teacher Agents application."""

from fastapi import APIRouter, File, Form, UploadFile

router = APIRouter(prefix="/api", tags=["api"])

chat_sessions: dict[str, list[dict]] = {}


@router.get("/")
async def api_root() -> dict[str, str]:
    """API info."""
    return {"message": "API v1"}


@router.post("/chat")
async def chat(
    audio: UploadFile = File(...),
    chat_id: str = Form(...),
):
    """Receive an audio recording and return a response.

    Keeps conversation context via chat_id.
    """
    audio_bytes = await audio.read()

    if chat_id not in chat_sessions:
        chat_sessions[chat_id] = []

    chat_sessions[chat_id].append({
        "role": "user",
        "audio_size": len(audio_bytes),
        "content_type": audio.content_type,
    })

    turn_number = len([m for m in chat_sessions[chat_id] if m["role"] == "user"])
    response_text = (
        f"Received audio message ({len(audio_bytes):,} bytes). "
        f"This is turn {turn_number} in the conversation."
    )

    chat_sessions[chat_id].append({
        "role": "assistant",
        "content": response_text,
    })

    return {
        "chat_id": chat_id,
        "response": response_text,
        "turn": turn_number,
    }
