# Creative Director Engine - Product Memory

The Creative Director Engine is a FastAPI-powered performance marketing engine. It transforms campaign briefs and brand parameters into fully packaged, deployable ad creatives and structured short-form video strategies.

---

## 🎯 Purpose and Target Audience
- **Target Users**: Growth marketers, startup founders, media buyers, and automated marketing agents (like Marko AI).
- **Core Value Proposition**: Rapid, high-converting creative ideation and asset production, bridging the gap between raw copy hooks and final visual assets (images/videos).
- **Domain Focus**: Direct-response marketing, digital advertisements (Meta, Google, TikTok), and viral organic video scripts (Instagram Reels).

---

## 🚀 Core Features

### 1. Hook & Messaging Angle Generation
- **Hooks**: Generates 10 to 20 scroll-stopping hook ideas across 5 distinct categories:
  - *Curiosity*: Creating an information gap.
  - *Fear-Based*: Identifying a critical risk or cost of inaction.
  - *Benefit-Driven*: Highlighting a concrete value or outcome.
  - *Contrarian*: Refuting a commonly accepted industry myth.
  - *Social-Proof*: Leveraging validation from customers or numbers.
- **Messaging Angles**: Builds 3 to 7 strategic sales arguments containing detailed descriptions, target emotional triggers, and exact customer use cases.

### 2. Platform-Specific Copywriting
- Produces platform-aware ad copy variations (Primary Text, Headline, CTA, Description).
- Enforces strict character limits, word limits, and style parameters optimized for:
  - **Meta / Facebook / Instagram**
  - **Google Search & Display**
  - **TikTok Ads**

### 3. Visual Concept Generation
- Plans structured visual designs tailored for image generation models (Vertex AI, HuggingFace Flux, NanoBanana).
- Enforces the **Zero Meta-Composition Rule** (avoiding screens-within-screens, hand-held device frames, or stock-photo humans) to produce premium, product-first commercial hero shots.

### 4. Parallel Asset Generation & Rendering
- **Multi-Provider Client Routing**: Automatically routes requests between Vertex AI (Gemini/Imagen), HuggingFace clients, and NanoBanana API endpoints.
- **Local Fallback Service**: Synthesizes placeholder images locally if API keys are absent or endpoints throttle.
- **Rendering & Composition**: Merges the generated image with brand logo files, overlays, color palettes, and fonts using `AdCompositionService` and outputs final assets.
- **Preview Generation**: Generates contextual mockups of ads in native social feeds (e.g., Instagram feed mockup).

### 5. Multi-Criteria Scoring & Ranking
- Rates all creative variants using Groq LLM evaluations based on four core parameters:
  - **Clarity**: Ease of comprehension.
  - **Persuasion**: Scroll-stopping tension or aspiration.
  - **CTA Alignment**: Relevance of the call-to-action.
  - **Platform Fit**: Clean styling within social guidelines.

### 6. Short-Form Video & Reels Intelligence
- **Instagram Analyzer**: Scrapes and analyzes transcripts and metadata from competitor accounts or trend logs.
- **ScriptWriter & ReelsDirector**: Produces detailed, shot-by-shot 9:16 video scripts detailing spoken dialogue, camera movements, overlay text, B-roll recommendations, music cues, and target retention spikes.
- **Retention Scorer**: Predicts watch-time drop-offs and viral potential before production begins.
