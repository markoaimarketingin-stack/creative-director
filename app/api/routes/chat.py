import asyncio
import logging

from fastapi import APIRouter
from pydantic import BaseModel
import httpx
from app.core.config import get_settings

router = APIRouter()
log = logging.getLogger("chat")


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

    error_msgs: list[str] = []
    reply: str | None = None
    hit_rate_limit = False

    # --- Try Groq first ---
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
                if response.status_code == 429:
                    hit_rate_limit = True
                    log.warning("[CHAT] Groq returned 429 Too Many Requests — will try Gemini")
                    error_msgs.append("Groq: rate limited (429)")
                else:
                    response.raise_for_status()
                    data = response.json()
                    reply = data["choices"][0]["message"]["content"].strip()
                    log.info("[CHAT] Groq responded OK")
        except Exception as exc:
            log.warning(f"[CHAT] Groq failed: {exc}")
            error_msgs.append(f"Groq error: {exc}")
    else:
        log.warning("[CHAT] groq_api_key not configured — skipping Groq")

    # --- Fall back to Gemini with retry on 429 ---
    if not reply and settings.gemini_api_key:
        max_attempts = 2
        for attempt in range(max_attempts):
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
                    payload: dict = {
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

                    if response.status_code == 429:
                        hit_rate_limit = True
                        wait_secs = 4 * (attempt + 1)
                        log.warning(
                            f"[CHAT] Gemini 429 (attempt {attempt + 1}/{max_attempts}) — "
                            f"{'retrying in ' + str(wait_secs) + 's' if attempt < max_attempts - 1 else 'giving up'}"
                        )
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(wait_secs)
                            continue
                        else:
                            error_msgs.append("Gemini: rate limited (429)")
                            break

                    response.raise_for_status()
                    data = response.json()
                    reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    log.info("[CHAT] Gemini responded OK")
                    break

            except Exception as exc:
                log.warning(f"[CHAT] Gemini error (attempt {attempt + 1}): {exc}")
                error_msgs.append(f"Gemini error: {exc}")
                break
    elif not reply:
        log.warning("[CHAT] gemini_api_key not configured — no fallback available")

    # --- Return reply or friendly error ---
    if reply:
        chat_db.save_message(session_id, "user", request.message)
        chat_db.save_message(session_id, "assistant", reply)
        new_history = history + [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": reply},
        ]
        return ChatResponse(reply=reply, context={"history": new_history}, session_id=session_id)
    else:
        if hit_rate_limit:
            friendly = (
                "The AI assistant is rate-limited right now. "
                "Please wait 10–15 seconds and try again."
            )
        else:
            errors = " | ".join(error_msgs) or "No API keys configured."
            friendly = f"Sorry, I couldn't reach the AI backend. ({errors})"
        log.error(f"[CHAT] All providers failed: {' | '.join(error_msgs)}")
        return ChatResponse(reply=friendly, context=request.context, session_id=session_id)

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

@router.get("/session-data/{session_id}")
async def get_session_data(session_id: str):
    """Get all session data: chat history, knowledge base, and execution history."""
    settings = get_settings()
    from app.services.database import ChatDatabase
    chat_db = ChatDatabase(settings)
    
    chat_history = chat_db.get_history(session_id)
    knowledge_base = chat_db.get_knowledge_base(session_id)
    execution_history = chat_db.get_execution_history(session_id)
    
    return {
        "session_id": session_id,
        "chat_history": chat_history,
        "knowledge_base": knowledge_base,
        "execution_history": execution_history,
    }

@router.post("/knowledge-base/{session_id}")
async def save_knowledge_base(session_id: str, kb_item: dict):
    """Save a knowledge base item to the session."""
    settings = get_settings()
    from app.services.database import ChatDatabase
    chat_db = ChatDatabase(settings)
    
    kb_id = chat_db.save_knowledge_base_item(
        session_id=session_id,
        file_name=kb_item.get("file_name", "unknown"),
        file_type=kb_item.get("file_type", "text"),
        file_path=kb_item.get("file_path", ""),
        file_content=kb_item.get("file_content"),
        metadata=kb_item.get("metadata", {}),
    )
    
    return {"success": kb_id is not None, "kb_id": kb_id, "session_id": session_id}

@router.get("/knowledge-base/{session_id}")
async def get_knowledge_base(session_id: str):
    """Retrieve all knowledge base items for a session."""
    settings = get_settings()
    from app.services.database import ChatDatabase
    chat_db = ChatDatabase(settings)
    
    knowledge_base = chat_db.get_knowledge_base(session_id)
    return {"session_id": session_id, "knowledge_base": knowledge_base}

@router.post("/execution-history/{session_id}")
async def save_execution_history(session_id: str, execution: dict):
    """Save execution/generation history."""
    settings = get_settings()
    from app.services.database import ChatDatabase
    import time
    
    chat_db = ChatDatabase(settings)
    start_time = time.time()
    
    execution_id = chat_db.save_execution_history(
        session_id=session_id,
        campaign_name=execution.get("campaign_name", "unknown"),
        execution_type=execution.get("execution_type", "generation"),
        input_data=execution.get("input_data", {}),
        output_data=execution.get("output_data", {}),
        status=execution.get("status", "success"),
        error_message=execution.get("error_message"),
        execution_time_ms=int((time.time() - start_time) * 1000),
    )
    
    return {"success": execution_id is not None, "execution_id": execution_id, "session_id": session_id}

@router.get("/execution-history/{session_id}")
async def get_execution_history(session_id: str):
    """Retrieve execution history for a session."""
    settings = get_settings()
    from app.services.database import ChatDatabase
    chat_db = ChatDatabase(settings)
    
    execution_history = chat_db.get_execution_history(session_id)
    return {"session_id": session_id, "execution_history": execution_history}