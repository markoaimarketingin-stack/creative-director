"""
Execute Endpoint - Global Supervisor Integration.

Exposes the standardized POST /execute and GET /health endpoints
that allow the global Marko AI Supervisor to call and discover this service.
"""

import asyncio
import logging
from time import perf_counter
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.api.contracts import ExecuteRequest, HealthResponse, AgentOutputContract
from app.services.integration_serializer import (
    serialize_error_response,
    serialize_to_v1,
)
from app.services.task_router import route_task
from app.models import CreativeInput, Platform, Objective

router = APIRouter(tags=["supervisor-integration"])
log = logging.getLogger("execute")

AGENT_NAME = "creative_director_agent"
DEFAULT_TIMEOUT_SECONDS = 30.0


@router.get("/health")
async def health() -> HealthResponse:
    """
    Health check endpoint required by Render health probes and supervisor discovery.

    Returns:
        Service status and version info.
    """
    return HealthResponse(
        status="ok",
        service=AGENT_NAME,
        version="1.0.0",
    )


@router.post("/execute")
async def execute(request: ExecuteRequest, fastapi_request: Request) -> Dict[str, Any]:
    """
    Entry point called by the global Marko AI Supervisor.

    This endpoint:
      1. Receives a standardized ExecuteRequest with trace_id, run_id, session_id
      2. Routes the request to appropriate internal services
      3. Aggregates results into a V1 AgentOutputContract packet
      4. Returns the packet (never raises HTTP 500)

    Args:
        request: The supervisor execution request
        fastapi_request: The raw FastAPI request to access application state

    Returns:
        AgentOutputContract as a dict (ready for JSON serialization)
    """
    started = perf_counter()

    # Log incoming request with trace identifiers
    log.info(
        "execute called trace_id=%s run_id=%s session_id=%s task=%s",
        request.trace_id,
        request.run_id,
        request.session_id,
        request.task or "auto",
    )

    try:
        # Step 1: Validate and extract request
        message = request.user_input.message or ""
        if not message.strip():
            log.warning(
                "execute called with empty message trace_id=%s run_id=%s",
                request.trace_id,
                request.run_id,
            )
            return serialize_error_response(
                agent_name=AGENT_NAME,
                error_type="validation_error",
                error_code="EMPTY_INPUT",
                error_message="user_input.message is empty or missing",
                started_at=started,
                error_details={"field": "user_input.message"},
            ).model_dump()

        # Step 2: Route to internal services
        services = route_task(request)
        log.info(
            "routed to services trace_id=%s run_id=%s services=%s",
            request.trace_id,
            request.run_id,
            services,
        )

        # Step 3: Run internal orchestration
        container = fastapi_request.app.state.container
        internal_result = await run_internal_orchestration(
            trace_id=request.trace_id,
            run_id=request.run_id,
            session_id=request.session_id,
            message=message,
            services=services,
            context=request.context,
            container=container,
        )

        # Step 4: Serialize to V1 contract
        output = serialize_to_v1(
            agent_name=AGENT_NAME,
            internal_result=internal_result,
            services_used=services,
            started_at=started,
        )

        log.info(
            "execute completed trace_id=%s run_id=%s status=%s insights=%d opportunities=%d",
            request.trace_id,
            request.run_id,
            output.status,
            len(output.insights),
            len(output.opportunities),
        )

        return output.model_dump()

    except asyncio.TimeoutError:
        log.error(
            "execute timeout trace_id=%s run_id=%s",
            request.trace_id,
            request.run_id,
        )
        return serialize_error_response(
            agent_name=AGENT_NAME,
            error_type="timeout",
            error_code="AGENT_TIMEOUT",
            error_message=f"Execution exceeded {DEFAULT_TIMEOUT_SECONDS}s timeout",
            started_at=started,
        ).model_dump()

    except ValidationError as e:
        log.error(
            "execute validation error trace_id=%s run_id=%s error=%s",
            request.trace_id,
            request.run_id,
            str(e),
        )
        return serialize_error_response(
            agent_name=AGENT_NAME,
            error_type="validation_error",
            error_code="INVALID_REQUEST",
            error_message=f"Request validation failed: {str(e)[:200]}",
            started_at=started,
        ).model_dump()

    except Exception as exc:
        log.error(
            "execute failed trace_id=%s run_id=%s error=%s",
            request.trace_id,
            request.run_id,
            str(exc),
            exc_info=True,
        )
        return serialize_error_response(
            agent_name=AGENT_NAME,
            error_type="service_error",
            error_code="INTERNAL_ERROR",
            error_message=f"Internal service error: {str(exc)[:200]}",
            started_at=started,
        ).model_dump()


async def run_internal_orchestration(
    trace_id: str,
    run_id: str,
    session_id: str,
    message: str,
    services: list[str],
    context: Dict[str, Any],
    container: Any,
) -> Dict[str, Any]:
    """
    Run the internal service orchestration by calling actual generators and engines.

    Args:
        trace_id: Distributed trace ID from supervisor
        run_id: Execution run ID from supervisor
        session_id: User session ID from supervisor
        message: The user's creative request message
        services: List of internal service names to execute
        context: Supervisor context (user_id, org_id, workspace_id, onboarding, etc.)
        container: The ServiceContainer instance to retrieve services from

    Returns:
        Dict with 'insights' and 'opportunities' keys (as lists of dicts)
    """
    log.info(
        "starting internal orchestration trace_id=%s run_id=%s services=%s",
        trace_id,
        run_id,
        services,
    )

    # Extract onboarding context safely with defaults
    onboarding = context.get("onboarding", {}) if isinstance(context, dict) else {}
    if not onboarding:
        onboarding = {}

    brand_name = onboarding.get("brand_name") or context.get("brand_name") or "Marko AI"
    if not isinstance(brand_name, str) or len(brand_name) < 2:
        brand_name = "Marko AI"

    product_description = onboarding.get("product_description") or context.get("product_description") or message
    if not isinstance(product_description, str) or len(product_description) < 10:
        product_description = f"Creative strategy and ad campaign design for: {message}"

    target_audience = onboarding.get("target_audience") or context.get("target_audience") or "General Audience"
    if not isinstance(target_audience, str) or len(target_audience) < 3:
        target_audience = "General Audience"

    tone = onboarding.get("tone") or context.get("tone") or "persuasive"
    if not isinstance(tone, str) or len(tone) < 2:
        tone = "persuasive"

    key_benefits = onboarding.get("key_benefits") or context.get("key_benefits")
    if not key_benefits or not isinstance(key_benefits, list) or len(key_benefits) == 0:
        key_benefits = ["Faster ad creation and optimization"]
    key_benefits = [str(b) for b in key_benefits if b]
    if not key_benefits:
        key_benefits = ["Faster ad creation and optimization"]

    raw_platform = onboarding.get("platform") or context.get("platform") or "meta"
    try:
        platform = Platform(str(raw_platform).lower())
    except ValueError:
        platform = Platform.META

    raw_objective = onboarding.get("objective") or context.get("objective") or "conversions"
    try:
        objective = Objective(str(raw_objective).lower())
    except ValueError:
        objective = Objective.CONVERSIONS

    # Build Pydantic model for generators
    payload = CreativeInput(
        brand_name=brand_name,
        product_description=product_description,
        target_audience=target_audience,
        platform=platform,
        objective=objective,
        tone=tone,
        key_benefits=key_benefits,
        campaign_name=onboarding.get("campaign_name") or f"{brand_name} Campaign",
    )

    insights = []
    opportunities = []

    # 1. Hook Generator
    hooks = []
    if "hook_generator" in services or "ad_copy_generator" in services or "visual_concept_generator" in services or "scoring_service" in services:
        try:
            hooks = await container.engine._hook_generator.generate(payload)
            if "hook_generator" in services:
                for h in hooks:
                    insights.append({
                        "type": "hook_insight",
                        "description": f"Targeted hook: {h.text}",
                        "impact": 70.0,
                        "confidence": 0.8,
                        "sources": ["hook_generator"],
                        "details": {"hook_type": h.type, "rationale": h.rationale}
                    })
                    opportunities.append({
                        "type": "hook_opportunity",
                        "description": f"Deploy hook type: {h.type}",
                        "recommendation": f"Use this hook: '{h.text}'. Rationale: {h.rationale}",
                        "impact": 75.0,
                        "confidence": 0.8,
                        "effort": "low",
                        "sources": ["hook_generator"],
                        "details": {"hook_type": h.type}
                    })
        except Exception as exc:
            log.warning("hook_generator failed: %s", exc)

    # 2. Angle Generator
    angles = []
    if "angle_generator" in services or "ad_copy_generator" in services or "visual_concept_generator" in services or "scoring_service" in services:
        try:
            angles = await container.engine._angle_generator.generate(payload)
            if "angle_generator" in services:
                for a in angles:
                    opportunities.append({
                        "type": "messaging_angle",
                        "description": f"Messaging Angle: {a.name}",
                        "recommendation": f"Target {a.target_emotion} emotion by positioning: {a.description}. Use case: {a.use_case}",
                        "impact": 80.0,
                        "confidence": 0.85,
                        "effort": "medium",
                        "sources": ["angle_generator"],
                        "details": {"target_emotion": a.target_emotion, "use_case": a.use_case}
                    })
        except Exception as exc:
            log.warning("angle_generator failed: %s", exc)

    # 3. Ad Copy Generator
    copies = []
    if "ad_copy_generator" in services or "visual_concept_generator" in services or "scoring_service" in services:
        try:
            if not hooks:
                from app.services.generators import _fallback_hooks
                hooks = _fallback_hooks(payload)
            if not angles:
                from app.services.generators import _fallback_angles
                angles = _fallback_angles(payload)
            copies = await container.engine._ad_copy_generator.generate(payload, hooks, angles)
            if "ad_copy_generator" in services:
                for cp in copies:
                    opportunities.append({
                        "type": "ad_copy_opportunity",
                        "description": f"Ad copy copy_id={cp.copy_id}",
                        "recommendation": f"Headline: {cp.headline} | Primary Text: {cp.primary_text} | CTA: {cp.cta}",
                        "impact": 85.0,
                        "confidence": 0.9,
                        "effort": "low",
                        "sources": ["ad_copy_generator"],
                        "details": {
                            "headline": cp.headline,
                            "primary_text": cp.primary_text,
                            "cta": cp.cta,
                            "description": cp.description
                        }
                    })
        except Exception as exc:
            log.warning("ad_copy_generator failed: %s", exc)

    # 4. Visual Concept Generator
    visual_concepts = []
    if "visual_concept_generator" in services or "scoring_service" in services:
        try:
            if not hooks:
                from app.services.generators import _fallback_hooks
                hooks = _fallback_hooks(payload)
            if not angles:
                from app.services.generators import _fallback_angles
                angles = _fallback_angles(payload)
            if not copies:
                from app.services.generators import _fallback_ad_copies
                copies = _fallback_ad_copies(payload, hooks, angles)
            visual_concepts = await container.engine._visual_concept_generator.generate(payload, hooks, angles, copies)
            if "visual_concept_generator" in services:
                for vc in visual_concepts:
                    opportunities.append({
                        "type": "visual_concept",
                        "description": f"Visual concept concept_id={vc.concept_id}",
                        "recommendation": f"Scene: {vc.scene_description} | Background: {vc.background_setting}",
                        "impact": 75.0,
                        "confidence": 0.8,
                        "effort": "medium",
                        "sources": ["visual_concept_generator"],
                        "details": {
                            "camera_angle": vc.camera_angle,
                            "mood": vc.mood,
                            "style_reference": vc.style_reference,
                            "aspect_ratio": vc.aspect_ratio,
                            "generation_prompt": vc.generation_prompt
                        }
                    })
        except Exception as exc:
            log.warning("visual_concept_generator failed: %s", exc)

    # 5. Scoring Service
    if "scoring_service" in services:
        try:
            if not hooks:
                from app.services.generators import _fallback_hooks
                hooks = _fallback_hooks(payload)
            if not angles:
                from app.services.generators import _fallback_angles
                angles = _fallback_angles(payload)
            if not copies:
                from app.services.generators import _fallback_ad_copies
                copies = _fallback_ad_copies(payload, hooks, angles)
            if not visual_concepts:
                from app.services.generators import _fallback_visual_concepts
                visual_concepts_drafts = _fallback_visual_concepts(payload, hooks, angles)
                from app.models import VisualConcept
                visual_concepts = [
                    VisualConcept(
                        concept_id=f"concept-{i:02d}",
                        hook_text=v.hook_text,
                        angle_name=v.angle_name,
                        scene_description=v.scene_description,
                        camera_angle=v.camera_angle,
                        background_setting=v.background_setting,
                        color_palette=v.color_palette,
                        mood=v.mood,
                        style_reference=v.style_reference,
                        aspect_ratio=v.aspect_ratio,
                        media_type=v.media_type,
                        generation_prompt=v.scene_description
                    ) for i, v in enumerate(visual_concepts_drafts, start=1)
                ]
            
            from app.models import GeneratedCreative, CreativeStatus
            gen_creatives = [
                GeneratedCreative(
                    concept_id=vc.concept_id,
                    provider="fallback",
                    status=CreativeStatus.SKIPPED,
                    prompt=vc.generation_prompt,
                    image_urls=[],
                    error="Scoring run without generation"
                ) for vc in visual_concepts
            ]
            scored = await container.engine._scoring_service.score(payload, visual_concepts, copies, gen_creatives)
            for sc in scored:
                insights.append({
                    "type": "creative_score",
                    "description": f"Creative score for concept_id={sc.concept_id}: {sc.total_score}",
                    "impact": float(sc.total_score),
                    "confidence": 0.9,
                    "sources": ["scoring_service"],
                    "details": {
                        "emotional_intensity": sc.emotional_intensity,
                        "clarity": sc.clarity,
                        "uniqueness": sc.uniqueness,
                        "platform_fit": sc.platform_fit,
                        "persuasion": sc.persuasion,
                        "cta_alignment": sc.cta_alignment,
                        "rationale": sc.rationale
                    }
                })
        except Exception as exc:
            log.warning("scoring_service failed: %s", exc)

    # 6. Instagram Reels Engine
    if "instagram_engine" in services:
        try:
            from app.models import InstagramDirectReelRequest
            direct_req = InstagramDirectReelRequest(
                brief=message,
                brand_name=brand_name,
                niche=onboarding.get("niche") or "marketing",
                audience=target_audience,
                creator_persona=onboarding.get("creator_persona") or "expert",
                goal=onboarding.get("goal") or "engagement",
                tone=tone,
            )
            response = await container.instagram_engine.direct_reel(direct_req)
            
            for item in response.analysis:
                insights.append({
                    "type": "instagram_reel_insight",
                    "description": f"Reel analysis: {item.insight}",
                    "impact": float(item.score),
                    "confidence": 0.85,
                    "sources": ["instagram_engine"],
                    "details": {
                        "category": item.category.value if hasattr(item.category, "value") else str(item.category),
                        "why_it_works": item.why_it_works,
                        "evidence": item.evidence
                    }
                })
            
            if response.script and response.script.spoken_script:
                opportunities.append({
                    "type": "reel_script",
                    "description": f"Viral Reel Script: {response.title}",
                    "recommendation": f"Script: {response.script.spoken_script}",
                    "impact": float(response.viral_probability_score),
                    "confidence": float(response.audience_retention_prediction) / 100.0 if response.audience_retention_prediction else 0.8,
                    "effort": "high",
                    "sources": ["instagram_engine"],
                    "details": {
                        "caption": response.instagram_caption,
                        "hashtags": response.hashtags,
                        "thumbnail_text": response.thumbnail_text
                    }
                })
                
            for note in response.director_notes:
                opportunities.append({
                    "type": "reel_director_note",
                    "description": f"Director recommendation: {note}",
                    "recommendation": note,
                    "impact": 70.0,
                    "confidence": 0.8,
                    "effort": "medium",
                    "sources": ["instagram_engine"],
                    "details": {}
                })
        except Exception as exc:
            log.warning("instagram_engine failed: %s", exc)

    # 7. Trend Detector
    if "trend_detector" in services:
        try:
            from app.models import InstagramDetectTrendsRequest
            trend_req = InstagramDetectTrendsRequest(
                brief=message,
                brand_name=brand_name,
                niche=onboarding.get("niche") or "marketing",
                audience=target_audience,
                tone=tone,
            )
            response = await container.instagram_engine.detect_trends(trend_req)
            for trend in response.trend_objects:
                insights.append({
                    "type": "trend_insight",
                    "description": f"Trend: {trend.trend_name} (score: {trend.trend_score})",
                    "impact": float(trend.trend_score),
                    "confidence": float(trend.viral_probability) / 100.0 if trend.viral_probability else 0.8,
                    "sources": ["trend_detector"],
                    "details": {
                        "saturation_level": trend.saturation_level,
                        "best_niches": trend.best_niches,
                        "source_count": trend.source_count
                    }
                })
                opportunities.append({
                    "type": "trend_opportunity",
                    "description": f"Capitalize on trend: {trend.trend_name}",
                    "recommendation": f"Hook: {', '.join(trend.hook_examples)}. Styles: {', '.join(trend.editing_styles)}",
                    "impact": float(trend.trend_score),
                    "confidence": float(trend.viral_probability) / 100.0 if trend.viral_probability else 0.8,
                    "effort": "medium",
                    "sources": ["trend_detector"],
                    "details": {
                        "caption_patterns": trend.caption_patterns,
                        "retention_levers": trend.retention_levers
                    }
                })
        except Exception as exc:
            log.warning("trend_detector failed: %s", exc)

    return {
        "insights": insights,
        "opportunities": opportunities,
        "metadata": {
            "trace_id": trace_id,
            "run_id": run_id,
            "session_id": session_id,
            "services_executed": services,
            "user_id": context.get("user_id"),
            "organization_id": context.get("organization_id"),
        },
    }

