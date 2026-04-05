from fastapi import APIRouter
from pydantic import BaseModel
import httpx
from app.core.config import get_settings

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: dict | None = None


class ChatResponse(BaseModel):
    reply: str
    context: dict | None = None






@router.post("/chat-assistant", response_model=ChatResponse)
async def chat_assistant(request: ChatRequest):
    settings = get_settings()

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

            new_history = history + [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": reply},
            ]

            return ChatResponse(reply=reply, context={"history": new_history})

    except Exception as e:
        return ChatResponse(
            reply=f"Sorry, I couldn't connect to the AI backend. Error: {str(e)}",
            context=request.context,
        )