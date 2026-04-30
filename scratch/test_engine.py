import asyncio
import os
from dotenv import load_dotenv
from app.core.config import Settings
from app.services.engine import ServiceContainer
from app.models import CreativeInput, Platform, Objective

load_dotenv()

async def test_engine():
    settings = Settings()
    container = ServiceContainer(settings)
    engine = container.engine

    payload = CreativeInput(
        brand_name="TestBrand",
        product_description="A revolutionary tool for marketers to create ads faster.",
        target_audience="Performance Marketers",
        tone="Professional",
        key_benefits=["Speed", "AI-powered creative", "Higher CTR"],
        platform=Platform.META,
        objective=Objective.TRAFFIC,
        hook_count=10,
        angle_count=3,
        copy_count=5,
        concept_count=1
    )

    print("--- Starting Campaign Generation ---")
    try:
        package = await engine.generate_campaign(payload)
        print("Campaign generated successfully!")
        print(f"Campaign Name: {package.campaign_name}")
        print(f"Hooks: {len(package.hooks)}")
        print(f"Ad Copies: {len(package.ad_copies)}")
        print(f"Visual Concepts: {len(package.visual_concepts)}")
        print(f"Generated Creatives: {len(package.generated_creatives)}")
        
        for creative in package.generated_creatives:
            print(f" - Provider: {creative.provider}")
            print(f" - Status: {creative.status}")
            if creative.error:
                print(f" - Error: {creative.error}")
            if creative.image_urls:
                print(f" - Image URL: {creative.image_urls[0][:100]}...")

    except Exception as e:
        print(f"Engine test FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await container.aclose()

if __name__ == "__main__":
    asyncio.run(test_engine())
