#!/usr/bin/env python3
"""
Test script to generate a single creative with Vertex AI image generation.
Tests the updated prompt with proper text rendering instructions.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import Settings
from app.models import CreativeInput, Objective, Platform
from app.providers.groq_llm import GroqLLMProvider
from app.providers.vertex_ai import VertexAIClient
from app.services.generators import (
    HookGenerator,
    MessagingAngleGenerator,
    AdCopyGenerator,
    VisualConceptGenerator,
)


async def test_generation():
    """Generate a complete creative with text rendering."""
    
    # Initialize settings from .env
    settings = Settings()
    
    print("=" * 80)
    print("VERTEX AI IMAGE GENERATION TEST")
    print("=" * 80)
    print()
    
    # Check configuration
    print("✓ Configuration Check:")
    print(f"  Project ID: {settings.vertex_ai_project_id}")
    print(f"  Location: {settings.vertex_ai_location}")
    print(f"  Model: {settings.vertex_ai_image_model}")
    print()
    
    # Create providers
    llm = GroqLLMProvider(settings)
    vertex_client = VertexAIClient(settings)
    
    # Create test payload
    payload = CreativeInput(
        brand_name="TechFlow Pro",
        product_description="Premium productivity software for teams that need real-time collaboration",
        target_audience="Busy professionals, project managers, tech-savvy millennials",
        key_benefits=["Real-time collaboration", "Zero setup time", "99.9% uptime guarantee"],
        tone="Professional, modern, confident",
        objective=Objective.CONVERSIONS,
        platform=Platform.META,
        hook_count=3,
        angle_count=2,
        copy_variations=2,
        visual_concept_count=1,
    )
    
    print("=" * 80)
    print("STEP 1: GENERATE HOOKS")
    print("=" * 80)
    hook_gen = HookGenerator(llm)
    hooks = await hook_gen.generate(payload)
    print(f"✓ Generated {len(hooks)} hooks:")
    for i, hook in enumerate(hooks, 1):
        print(f"  {i}. [{hook.type}] {hook.text}")
    print()
    
    print("=" * 80)
    print("STEP 2: GENERATE MESSAGING ANGLES")
    print("=" * 80)
    angle_gen = MessagingAngleGenerator(llm)
    angles = await angle_gen.generate(payload)
    print(f"✓ Generated {len(angles)} angles:")
    for i, angle in enumerate(angles, 1):
        print(f"  {i}. {angle.name}")
    print()
    
    print("=" * 80)
    print("STEP 3: GENERATE AD COPY")
    print("=" * 80)
    copy_gen = AdCopyGenerator(llm)
    ad_copies = await copy_gen.generate(payload, hooks, angles)
    print(f"✓ Generated {len(ad_copies)} ad copies:")
    for i, copy in enumerate(ad_copies, 1):
        print(f"  {i}. Headline: {copy.headline}")
        print(f"     Body: {copy.primary_text}")
        print(f"     CTA: {copy.cta}")
    print()
    
    print("=" * 80)
    print("STEP 4: GENERATE VISUAL CONCEPTS")
    print("=" * 80)
    concept_gen = VisualConceptGenerator(llm)
    concepts = await concept_gen.generate(payload, hooks, angles, ad_copies)
    print(f"✓ Generated {len(concepts)} visual concepts:")
    for i, concept in enumerate(concepts, 1):
        print(f"  {i}. {concept.scene_description}")
        print(f"     Style: {concept.style_reference}")
        print(f"     Colors: {', '.join(concept.color_palette)}")
    print()
    
    print("=" * 80)
    print("STEP 5: GENERATE IMAGE WITH VERTEX AI")
    print("=" * 80)
    
    if not concepts or not ad_copies:
        print("✗ No concepts or copies generated. Skipping image generation.")
        return
    
    concept = concepts[0]
    ad_copy = ad_copies[0]
    
    # Generate image with Vertex AI
    print(f"Generating image for:")
    print(f"  Concept: {concept.scene_description}")
    print(f"  Headline: {ad_copy.headline}")
    print(f"  Body: {ad_copy.primary_text}")
    print(f"  CTA: {ad_copy.cta}")
    print()
    
    try:
        generated_creatives = await vertex_client.generate_batch(
            [concept],
            platform=payload.platform,
            sample_images=None
        )
        
        if generated_creatives:
            creative = generated_creatives[0]
            print("✓ IMAGE GENERATION ATTEMPT COMPLETED!")
            print(f"  Status: {creative.status}")
            print(f"  Provider: {creative.provider}")
            if creative.error:
                print(f"  Error: {creative.error}")
            print(f"  Image URLs: {len(creative.image_urls)}")
            for i, url in enumerate(creative.image_urls, 1):
                print(f"    {i}. {url[:80]}..." if len(url) > 80 else f"    {i}. {url}")
            print()
            
            # Save metadata regardless of success/failure
            output_file = Path("test_output") / "vertex_test_metadata.json"
            output_file.parent.mkdir(exist_ok=True)
            
            metadata = {
                "status": creative.status.value if hasattr(creative.status, 'value') else str(creative.status),
                "error": creative.error,
                "brand": payload.brand_name,
                "platform": payload.platform.value,
                "hook": {
                    "text": ad_copy.hook_text,
                },
                "angle": ad_copy.angle_name,
                "ad_copy": {
                    "headline": ad_copy.headline,
                    "body": ad_copy.primary_text,
                    "cta": ad_copy.cta,
                },
                "visual_concept": {
                    "scene": concept.scene_description,
                    "camera_angle": concept.camera_angle,
                    "background": concept.background_setting,
                    "style": concept.style_reference,
                    "mood": concept.mood,
                    "colors": concept.color_palette,
                },
                "generated_creative": {
                    "provider": creative.provider,
                    "api_version": creative.provider_api_version,
                    "image_count": len(creative.image_urls),
                    "images": creative.image_urls,
                }
            }
            
            with open(output_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✓ Metadata saved to: {output_file}")
            print()
            
            if creative.status.value == "generated" and creative.image_urls:
                print("=" * 80)
                print("TEST COMPLETED SUCCESSFULLY!")
                print("=" * 80)
            elif creative.status.value == "failed":
                print("=" * 80)
                print("IMAGE GENERATION FAILED - DEBUG INFO:")
                print("=" * 80)
                print(f"Error: {creative.error}")
                print(f"Prompt: {creative.prompt}")
            else:
                print("=" * 80)
                print(f"TEST COMPLETED WITH STATUS: {creative.status.value}")
                print("=" * 80)
        else:
            print("✗ No creatives generated")
    
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_generation())
