from fastapi import APIRouter
from pydantic import BaseModel
import httpx
from app.core.config import get_settings

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: dict | None = None
    session_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    context: dict | None = None
    session_id: str | None = None






@router.post("/chat-assistant", response_model=ChatResponse)
async def chat_assistant(request: ChatRequest):
    settings = get_settings()
    from app.services.database import ChatDatabase
    import uuid
    chat_db = ChatDatabase(settings)
    session_id = request.session_id or str(uuid.uuid4())

    context = request.context or {}
    history = context.get("history", [])
    campaign = context.get("campaign", {})

    campaign_summary = ""
    if campaign:
        hooks = campaign.get("hooks", [])
        angles = campaign.get("angles", [])
        copies = campaign.get("copies", [])
        concepts = campaign.get("concepts", [])
        parts = []
        if hooks:
            parts.append("HOOKS:\n" + "\n".join(f"- [{h.get('type','')}] {h.get('text','')}" for h in hooks[:5]))
        if angles:
            parts.append("ANGLES:\n" + "\n".join(f"- {a.get('name','')}: {a.get('description','')}" for a in angles[:3]))
        if copies:
            parts.append("TOP COPY:\n" + "\n".join(f"- {c.get('headline','')}: {c.get('primary_text','')}" for c in copies[:3]))
        if concepts:
            parts.append("CONCEPTS:\n" + "\n".join(f"- {c.get('concept_id','')}: {c.get('scene_description','')}" for c in concepts[:2]))
        if parts:
            campaign_summary = "\n\nCURRENT CAMPAIGN OUTPUT:\n" + "\n\n".join(parts)

    system = f"""You are Marko, a sharp AI assistant built into Marko AI — an agentic platform for generating ad hooks, angles, copy, and visual concepts.

Rules:
- Reply in 1-2 sentences max. No fluff, no filler.
- Be direct. Lead with the answer, not context.
- If asked about the generated content, reference it specifically.
- If asked something off-topic, briefly answer and steer back to marketing/ads.
- Never say "Great question", "Of course", "Certainly", or any preamble.
- Tone: confident, sharp, like a senior growth marketer.{campaign_summary}"""

    messages = [{"role": "system", "content": system}]
    for entry in history[-10:]:
        messages.append(entry)
    messages.append({"role": "user", "content": request.message})

    error_msgs = []
    reply = None

    if settings.groq_api_key:
        try:
            async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.groq_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.groq_model,
                        "messages": messages,
                        "max_tokens": 512,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()
                reply = data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            error_msgs.append(f"Groq error: {str(e)}")

    if not reply and settings.gemini_api_key:
        try:
            gemini_messages = []
            system_instruction = ""
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                elif msg["role"] == "user":
                    gemini_messages.append({"role": "user", "parts": [{"text": msg["content"]}]})
                elif msg["role"] == "assistant":
                    gemini_messages.append({"role": "model", "parts": [{"text": msg["content"]}]})
            
            async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
                url = f"{settings.gemini_base_url}/{settings.gemini_model}:generateContent"
                payload = {
                    "contents": gemini_messages,
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 512,
                    }
                }
                if system_instruction:
                    payload["system_instruction"] = {
                        "parts": [{"text": system_instruction}]
                    }

                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    params={"key": settings.gemini_api_key},
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            error_msgs.append(f"Gemini error: {str(e)}")

    if reply:
        chat_db.save_message(session_id, "user", request.message)
        chat_db.save_message(session_id, "assistant", reply)

        new_history = history + [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": reply},
        ]
        return ChatResponse(reply=reply, context={"history": new_history}, session_id=session_id)
    else:
        errors = " | ".join(error_msgs) or "No API keys configured."
        return ChatResponse(
            reply=f"Sorry, I couldn't connect to the AI backend. Error: {errors}",
            context=request.context,
            session_id=session_id
        )

@router.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    settings = get_settings()
    from app.services.database import ChatDatabase
    chat_db = ChatDatabase(settings)
    history = chat_db.get_history(session_id)
    return {"session_id": session_id, "history": history}

@router.get("/chat-sessions")
async def get_chat_sessions():
    settings = get_settings()
    from app.services.database import ChatDatabase
    chat_db = ChatDatabase(settings)
    sessions = chat_db.get_sessions()
    return {"sessions": sessions}