# Creative Director Engine

Creative Director Engine is a FastAPI backend for Marko AI that turns a campaign brief into ready-to-execute creative packages:

- Hook generation
- Messaging angles
- Platform-specific ad copy
- Visual concept planning
- NanoBanana creative generation
- Scoring and ranking
- Local storage with optional S3 mirroring

The system is API-first. A frontend dashboard is intentionally left optional.

## Stack

- FastAPI
- Pydantic
- Groq chat completions with structured JSON outputs
- NanoBanana API adapter
- Local filesystem output with S3-ready mirroring

## Project layout

```text
app/
  api/routes/creatives.py
  core/config.py
  models/creative.py
  providers/groq_llm.py
  providers/nanobanana.py
  services/prompts.py
  services/generators.py
  services/scoring.py
  services/storage.py
  services/engine.py
examples/
  sample_request.json
  sample_response.json
  sample_prompts.md
output/
```

## Features

### 1. Hook generator

Generates 10 to 20 hooks across:

- Curiosity
- Fear-based
- Benefit-driven
- Contrarian
- Social-proof

### 2. Messaging angle generator

Generates 3 to 7 angles with:

- Description
- Target emotion
- Use case

### 3. Ad copy generator

Creates platform-aware copy variants with:

- `primary_text`
- `headline`
- `cta`
- `description`

The generator also post-processes character limits per platform.

### 4. Visual concept generator

Builds execution-ready concepts with:

- Scene description
- Camera angle
- Background setting
- Color palette
- Mood
- Style reference
- Aspect ratio

### 5. NanoBanana integration

The NanoBanana provider adapter:

- Prefers `/api/v2/images/generate`
- Falls back to `/api/v1/images/generate`
- Polls status endpoints when a task ID is returned
- Returns generated image or video URLs when available
- Gracefully marks assets as `skipped` or `failed` when generation cannot complete

### 6. Creative scoring engine

Each creative is ranked on:

- Emotional intensity
- Clarity
- Uniqueness
- Platform fit

### 7. Creative package builder

Every run persists:

- `input.json`
- `hooks.json`
- `angles.json`
- `ad_copy.json`
- `visual_concepts.json`
- `creative_scores.json`
- `creatives.json`
- `campaign_manifest.json`

## API

### `POST /generate-creatives`

Input schema:

```json
{
  "brand_name": "Marko AI",
  "product_description": "AI ad tool that generates hooks, copy, and creative strategy for founders.",
  "target_audience": "Startup founders and growth marketers",
  "platform": "meta",
  "objective": "conversions",
  "tone": "premium",
  "key_benefits": ["Faster ideation", "More hooks", "Sharper testing"],
  "competitors": ["Jasper", "Copy.ai"],
  "visual_style": "cinematic SaaS ads"
}
```

Response includes:

- Hooks
- Angles
- Ad copies
- Visual concepts
- Generated creatives
- Scores
- Packaged creative assets
- Output directory

### `GET /top-creatives`

Returns the highest-ranked creative assets from stored output packages.

Query params:

- `limit`
- `platform`

## Local setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
```

Set:

- `GROQ_API_KEY`
- `NANOBANANA_API_KEY`

Optional:

- `GROQ_MODEL`
- `GROQ_FALLBACK_MODELS`
- `GROQ_MAX_RETRIES`
- `GROQ_RETRY_BASE_DELAY_SECONDS`
- `OUTPUT_ROOT`
- `S3_BUCKET_NAME`
- `S3_REGION`

### 3. Run the API

```bash
uvicorn app.main:app --reload
```

### 4. Test the service

```bash
curl -X POST http://127.0.0.1:8000/generate-creatives ^
  -H "Content-Type: application/json" ^
  --data @examples/sample_request.json
```

## Output structure

Each campaign run is written to:

```text
output/
  campaign-slug/
    timestamp/
      hooks.json
      angles.json
      ad_copy.json
      visual_concepts.json
      creatives.json
      creative_scores.json
      campaign_manifest.json
```

## Notes

- `GROQ_API_KEY` is required for hooks, angles, copy, and visual concepts.
- Groq requests now use retry/backoff for transient failures and `429` responses.
- `GROQ_FALLBACK_MODELS` can be set as a comma-separated env value to try backup models when the primary model is throttled.
- `NANOBANANA_API_KEY` is required for actual image generation. Without it, the package still builds and marks generated assets as `skipped`.
- S3 upload is optional. If `S3_BUCKET_NAME` is set and `boto3` is installed, saved JSON artifacts are mirrored to S3.
- Sample request, response, and prompts live in [examples/sample_request.json](/d:/Marko%20AI-agents/Creative%20director/examples/sample_request.json), [examples/sample_response.json](/d:/Marko%20AI-agents/Creative%20director/examples/sample_response.json), and [examples/sample_prompts.md](/d:/Marko%20AI-agents/Creative%20director/examples/sample_prompts.md).
