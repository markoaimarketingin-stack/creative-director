# Creative Director Engine - Workflow Pipelines

This document details the step-by-step workflows of the Creative Director Engine, covering campaign generation, Instagram Reel scripting, and Supervisor integration.

---

## 🚀 1. Campaign Generation Workflow

The main campaign generation flow is managed by `CreativeDirectorEngine.generate_campaign()` (defined in [engine.py:L300](file:///c:/Users/abhis/Downloads/creativedir/creative-director/app/services/engine.py#L300)).

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client / API Caller
    participant Engine as CreativeDirectorEngine
    participant Ideator as Hook & Angle Generators
    participant Copywriter as AdCopy & VisualConcept Generators
    participant Mux as Provider Multiplexer
    participant Compositor as AdCompositionService
    participant Scorer as CreativeScoringService
    participant Archiver as CampaignStorage & DB

    Client->>Engine: POST /generate-creatives (CreativeInput brief)
    activate Engine
    
    %% Ideation Phase
    Engine->>Ideator: Generate Hooks & Angles (Parallel)
    activate Ideator
    Ideator-->>Engine: Returns list[Hook] & list[MessagingAngle]
    deactivate Ideator
    
    %% Copy & Scene Drafting
    Engine->>Copywriter: Generate Ad Copy & Visual Concepts
    activate Copywriter
    Copywriter-->>Engine: Returns list[AdCopy] & list[VisualConcept]
    deactivate Copywriter
    
    %% Parallel Image Synthesis
    loop For each VisualConcept
        Engine->>Mux: Generate Image (Parallel tasks)
        activate Mux
        Note over Mux: Routes to Vertex AI, HF, NanoBanana, or Fallback
        Mux-->>Engine: Returns GeneratedCreative (image url or bytes)
        deactivate Mux
    end
    
    %% Composition & Scoring
    Engine->>Compositor: Render Brand Assets
    activate Compositor
    Note over Compositor: Overlays logo, brand colors, fonts, CTAs
    Compositor-->>Engine: Returns list[CreativeAsset] with rendered image paths
    deactivate Compositor
    
    Engine->>Scorer: Evaluate Assets
    activate Scorer
    Note over Scorer: Scores clarity, persuasion, CTA, and platform fit
    Scorer-->>Engine: Returns scored list[CreativeAsset]
    deactivate Scorer
    
    %% Persistence
    Engine->>Archiver: Package and Save Campaign
    activate Archiver
    Note over Archiver: Writes files locally & saves metadata to Supabase
    Archiver-->>Engine: Returns saved CampaignPackage
    deactivate Archiver
    
    Engine-->>Client: Returns JSON response (CampaignPackage details)
    deactivate Engine
```

### Step-by-Step Breakdown:
1. **Brief Ingestion**: An API client calls `POST /generate-creatives` with parameters like brand name, audience, benefits, colors, logos, and target platform.
2. **Concept Stage**:
   - `HookGenerator` and `MessagingAngleGenerator` run concurrently using Pydantic validation via the Groq LLM client.
   - Using the output hooks and angles, `AdCopyGenerator` compiles copy combinations.
   - `VisualConceptGenerator` translates copy and branding directives into visual concepts, observing the **Zero Meta-Composition Rule**.
3. **Image Synthesis**:
   - `generate_single_image` selects the best provider:
     - **Vertex AI (Gemini/Imagen)** or **Hugging Face (Flux)** is preferred if the brief contains uploaded reference images.
     - **NanoBanana API** handles text-overlay generation when no references are provided.
     - **LocalImageFallbackService** runs if API keys are missing or failures occur.
4. **Rendering & Compositing**:
   - `AdCompositionService` downloads generated images, resizes them to the platform ratio, adds overlays, sets text positioning, and renders the logo image.
   - `AdPreviewGenerator` renders feeds cards (like an Instagram ad template) for preview.
5. **Scoring & Sorting**:
   - `CreativeScoringService` evaluates copy alignment, clarity, and aesthetics, sorting final assets in descending order of total score.
6. **Persistence**:
   - Files (`manifest.json`, copy, hooks, images, layouts) are saved locally under `output/campaign-slug/timestamp/`.
   - Manifest metadata is mirrored to Supabase.
   - Returns a structured `CampaignPackage` response.

---

## 📹 2. Instagram Reels Analysis & Scripting Pipeline

This pipeline parses existing short-form videos and drafts shoot-ready script director packages.

```mermaid
graph TD
    %% Sequence
    Ingest[1. Ingestion of Competitor URL/Brief] --> Analyze[2. InstagramAnalyzer Transcript Parsing]
    Analyze --> Pattern[3. ViralPatternEngine Hook Extraction]
    Pattern --> Trend[4. TrendDetector Audio & pacing alignment]
    Trend --> Script[5. ScriptWriter generates Dialogue & overlays]
    Script --> Direct[6. ReelsDirector builds shot-by-shot storyboard]
    Direct --> Score[7. RetentionScorer predicts drop-off points]
    Score --> Output[8. Shoot-Ready Reel Package]
```

### Step-by-Step Breakdown:
1. **Ingestion**: `InstagramIngestor` downloads metadata, transcript data, and metrics from video posts.
2. **Analysis**: `InstagramAnalyzer` reviews hooks, visual patterns, and transitions.
3. **Pattern Extraction**: `ViralPatternEngine` parses what hook types and structures successfully capture retention.
4. **Scriptwriting**: `ScriptWriter` drafts a creator-ready script incorporating speech, B-roll guides, screen captions, pacing markers, and loop triggers.
5. **Cinematic Direction**: `ReelsDirector` creates a storyboard detailing timeline sequences, camera movement angles (e.g., zooms, panning), B-roll visual details, caption colors, and audio triggers.
6. **Retention Scoring**: `RetentionScorer` rates the storyboard and script for viral probability and retention performance, suggesting changes before filming.

---

## 🔌 3. Supervisor Integration Execution Pipeline

This workflow governs how the engine responds when commanded by the autonomous supervisor via the `/execute` API endpoint.

```mermaid
sequenceDiagram
    autonumber
    actor Sup as Autonomous Supervisor
    participant Route as Execute Endpoint (/execute)
    participant Router as Task Router
    participant Engine as Internal Orchestration
    participant Serializer as V1 Output Serializer

    Sup->>Route: POST /execute (ExecuteRequest payload)
    activate Route
    Note over Route: Validates trace_id, run_id, session_id presence
    
    Route->>Router: Route task context (user_input message & task fields)
    activate Router
    Note over Router: Maps terms ('hook', 'copy', 'reel', etc.) to service lists
    Router-->>Route: Target sub-services
    deactivate Router
    
    Route->>Engine: Run Internal Orchestration (target services)
    activate Engine
    Note over Engine: Calls hook, copy, concept, or reels engine
    Engine-->>Route: Internal Results dictionary
    deactivate Engine
    
    Route->>Serializer: Serialize to V1 Format
    activate Serializer
    Note over Serializer: Computes deterministic IDs & clips values (impact 0-100, confidence 0-1)
    Serializer-->>Route: AgentOutputContract
    deactivate Serializer
    
    Route-->>Sup: Returns AgentOutputContract (status code 200)
    deactivate Route
```

### Step-by-Step Breakdown:
1. **Supervisor Call**: The supervisor issues a payload to `/execute`.
2. **Routing Decision**:
   - `task_router.py` checks for an explicit supervisor task list.
   - If empty, it runs keyword mapping on `user_input.message`:
     - *"hook"* -> Hook generator.
     - *"copy"* -> Ad copy generator.
     - *"visual"* -> Visual concept planner.
     - *"reel/video/instagram"* -> Instagram scripting engine.
3. **Engine Run**: Runs the designated generators. Logging templates include the current request's `trace_id`, `run_id`, and `session_id`.
4. **Contract Serialization**:
   - `integration_serializer.py` normalizes ratings: impact is clipped to `0-100`, confidence to `0-1`.
   - Generates deterministic IDs for insights/opportunities using `sha1(type + "|" + description)[:12]`.
   - **Error Handling Wrap**: If an exception or timeout occurs, the endpoint catches it and returns a valid `AgentOutputContract` with `status="failed"` and the error details inside the payload. It never fails with an HTTP 500 status.
