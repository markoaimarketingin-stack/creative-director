import json

from app.core.config import Settings


def render_homepage(settings: Settings) -> str:
    sample_payload = {
        "brand_name": "Marko AI",
        "product_description": "AI ad tool that generates hooks, ad copy, platform-specific strategy, and creative directions for founders.",
        "target_audience": "Startup founders and growth marketers who run paid acquisition in-house",
        "platform": "meta",
        "objective": "conversions",
        "tone": "premium",
        "key_benefits": [
            "Launch more ad variations in minutes",
            "Generate sharper hooks for cold traffic",
        ],
        "competitors": ["Jasper", "Copy.ai"],
        "visual_style": "cinematic SaaS ads with founder energy",
        "hook_count": 10,
        "angle_count": 3,
        "copy_count": 5,
        "concept_count": 2,
    }
    payload_text = json.dumps(sample_payload, indent=2)
    groq_status = "Connected" if settings.groq_api_key else "Missing key"
    nanobanana_status = "Unavailable" if not settings.nanobanana_api_key else "Configured"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{settings.app_name}</title>
  <style>
    :root {{ --bg:#0b1020; --panel:#141b2d; --soft:#1a2135; --line:#29324a; --text:#eef2ff; --muted:#8d98b8; --accent:#4c7dff; --accent-soft:#7c5cff; --dark:#0a0f1d; --success:#34d399; --warn:#f4c15d; }}
    * {{ box-sizing:border-box; }}
    html,body {{ height:100%; }}
    body {{ margin:0; font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--text); background:var(--bg); }}
    a {{ color:inherit; text-decoration:none; }}
    button {{ font:inherit; cursor:pointer; }}
    .app {{ min-height:100vh; display:grid; grid-template-columns:240px minmax(0,1fr) 360px; background:var(--bg); }}
    .sidebar {{ background:#090e1c; color:#fff; padding:22px 12px; display:flex; flex-direction:column; border-right:1px solid rgba(124,137,178,.16); }}
    .logo {{ display:flex; align-items:center; gap:14px; font-weight:800; font-size:1.05rem; margin-bottom:28px; }}
    .logo-mark {{ width:42px; height:42px; border-radius:14px; background:linear-gradient(135deg,#7c5cff 0%,#4c7dff 100%); color:#fff; display:grid; place-items:center; font-weight:900; box-shadow:0 12px 24px rgba(76,125,255,.22); }}
    .label {{ color:#667291; text-transform:uppercase; letter-spacing:.08em; font-size:.74rem; margin:18px 10px 10px; }}
    .nav {{ display:grid; gap:8px; }}
    .nav-item {{ display:flex; align-items:center; gap:12px; padding:14px 16px; border-radius:16px; color:#aab5d2; border:1px solid transparent; background:transparent; transition:background .18s ease,border-color .18s ease,color .18s ease; }}
    .nav-item.active {{ background:#101937; color:#eff3ff; border-color:#1d2a55; box-shadow:inset 3px 0 0 #4c7dff; }}
    .specialist {{ color:#9eabcb; background:transparent; border:1px solid transparent; }}
    .specialist:not(.active) {{ color:#9eabcb; background:transparent; border-color:transparent; }}
    .specialist.active {{ background:#101937; color:#ffffff; border-color:#1d2a55; }}
    .ic {{ width:28px; height:28px; border-radius:9px; display:grid; place-items:center; background:rgba(255,255,255,.04); transition:background .18s ease; }}
    .specialist.active .ic, .nav-item.active .ic {{ background:rgba(76,125,255,.16); color:#c8d7ff; }}
    .user {{ margin-top:auto; padding:14px 12px 0; border-top:1px solid rgba(124,137,178,.12); display:flex; align-items:center; gap:12px; }}
    .avatar {{ width:38px; height:38px; border-radius:50%; background:#fff; color:#111; display:grid; place-items:center; font-weight:800; font-size:.82rem; }}
    .main {{ display:flex; flex-direction:column; min-width:0; min-height:100vh; border-right:1px solid rgba(124,137,178,.12); background:#12182a; }}
    .content {{ flex:1; display:grid; grid-template-rows:minmax(0,1fr) auto; min-height:0; }}
    .canvas {{ padding:24px; overflow:auto; background:#12182a; }}
    .hero {{ border:none; border-radius:0; background:transparent; min-height:100%; padding:0; display:block; text-align:left; }}
    h1 {{ margin:0 0 10px; font-size:clamp(2.2rem,3vw,3rem); line-height:1.02; letter-spacing:-.04em; font-weight:900; color:#f6f8ff; }}
    h2, h3, strong {{ margin:0 0 8px; }}
    p {{ margin:0; color:#8d98b8; line-height:1.65; }}
    .cta {{ display:flex; gap:14px; flex-wrap:wrap; justify-content:flex-start; margin-top:24px; }}
    .cta button {{ min-height:50px; padding:0 24px; border-radius:16px; border:1px solid rgba(124,137,178,.18); background:#171f35; color:#eff3ff; font-weight:700; }}
    .cta button:first-child {{ background:linear-gradient(135deg,#4c7dff 0%,#5c6dff 100%); border-color:transparent; }}
    .results-panel, .loading-panel {{ border:1px solid rgba(124,137,178,.14); border-radius:24px; background:#171f32; padding:20px 18px; box-shadow:none; }}
    .results-panel {{ margin-top:18px; }}
    .loading-panel {{ margin-top:18px; padding:40px 28px; background:#171f32; }}
    .loading-shell {{ display:grid; place-items:center; min-height:300px; text-align:center; }}
    .loading-shell h2 {{ margin-bottom:10px; }}
    .loading-shell p {{ max-width:520px; }}
    .loading-dots {{ display:inline-flex; gap:8px; margin-top:18px; }}
    .loading-dots span {{ width:10px; height:10px; border-radius:999px; background:#2d5bff; opacity:.25; animation:bounceDots 1s infinite ease-in-out; }}
    .loading-dots span:nth-child(2) {{ animation-delay:.15s; }}
    .loading-dots span:nth-child(3) {{ animation-delay:.3s; }}
    @keyframes bounceDots {{
      0%, 80%, 100% {{ transform:translateY(0); opacity:.25; }}
      40% {{ transform:translateY(-6px); opacity:1; }}
    }}
    .tabs {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:2px; }}
    .tab {{ min-height:38px; padding:0 14px; border-radius:999px; border:1px solid rgba(124,137,178,.16); background:#11182b; color:#9eabcb; font-size:.84rem; font-weight:700; display:inline-flex; align-items:center; gap:8px; }}
    .tab.active {{ background:#4c7dff; border-color:#4c7dff; color:#fff; }}
    .tab-count {{ min-width:22px; height:22px; padding:0 6px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:#1f2842; color:#c4d0ef; font-size:.76rem; font-weight:800; }}
    .tab.active .tab-count {{ background:rgba(255,255,255,.16); color:#fff; }}
    .card {{ background:#1b2338; border:1px solid rgba(124,137,178,.14); border-radius:18px; padding:14px; }}
    .section-panel {{ margin-top:16px; }}
    .section-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:12px; }}
    .section-kicker {{ color:#7f8aa7; font-size:.88rem; }}
    .section-count {{ min-width:36px; height:36px; padding:0 10px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:#141c30; color:#dce5ff; font-size:.84rem; font-weight:800; border:1px solid rgba(124,137,178,.14); }}
    .single-stack {{ display:grid; gap:12px; max-height:420px; overflow:auto; padding-right:4px; }}
    .mono {{ font:.82rem/1.5 Consolas,"Courier New",monospace; white-space:pre-wrap; word-break:break-word; color:#95a3c5; margin-top:8px; }}
    .status-line {{ color:#7f8aa7; font-size:.9rem; min-height:20px; }}
    .composer-wrap {{ padding:14px 24px 20px; border-top:1px solid rgba(124,137,178,.12); background:#12182a; }}
    .composer {{ border:1px solid rgba(124,137,178,.16); background:#171f35; border-radius:22px; min-height:76px; display:grid; grid-template-columns:auto 1fr auto; gap:12px; padding:12px 14px; }}
    .tool, .send {{ width:34px; height:34px; border-radius:50%; display:grid; place-items:center; background:#1f2842; border:1px solid rgba(124,137,178,.16); color:#9eabcb; }}
    .send.ready {{ width:40px; height:40px; background:var(--accent); color:#fff; border:none; }}
    textarea {{ width:100%; min-height:96px; max-height:220px; border:none; resize:vertical; outline:none; font:.95rem/1.6 Consolas,"Courier New",monospace; color:#e6edff; background:transparent; padding-top:8px; }}
    .note {{ text-align:center; color:#667291; font-size:.88rem; margin-top:10px; }}
    .dashboard-title {{ margin-bottom:4px; }}
    .dashboard-subtitle {{ font-size:1rem; margin-bottom:22px; }}
    .brief-form {{ background:#171f32; border:1px solid rgba(124,137,178,.14); border-radius:22px; padding:22px; margin-bottom:22px; }}
    .brief-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-bottom:18px; }}
    .field {{ display:grid; gap:6px; }}
    .field.span-2 {{ grid-column:span 2; }}
    .field-label {{ color:#c9d3ef; font-size:.88rem; font-weight:700; }}
    .field-input {{ width:100%; border:1px solid rgba(124,137,178,.16); border-radius:12px; background:#11182b; color:#eef2ff; padding:10px 14px; font:inherit; outline:none; }}
    .field-input:focus {{ border-color:rgba(76,125,255,.5); }}
    .field-ta {{ min-height:80px; resize:vertical; }}
    .count-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .count-card {{ background:#141c30; border:1px solid rgba(124,137,178,.14); border-radius:14px; padding:12px; display:grid; gap:6px; }}
    .count-label {{ color:#7f8aa7; font-size:.82rem; }}
    .count-input {{ width:100%; border:none; outline:none; background:transparent; color:#f6f8ff; font-size:1.5rem; font-weight:900; }}
    .engine-title {{ font-size:1.5rem; font-weight:800; color:#f6f8ff; margin:0 0 6px; }}
    .engine-copy {{ color:#8d98b8; }}
    .engine-action {{ min-height:48px; padding:0 22px; border-radius:16px; border:none; background:linear-gradient(135deg,#4c7dff 0%,#5c6dff 100%); color:#fff; font-weight:800; box-shadow:0 14px 28px rgba(76,125,255,.22); }}
    .pipeline-card {{ background:#171f32; border:1px solid rgba(124,137,178,.14); border-radius:22px; padding:20px; }}
    .pipeline-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:14px; margin-bottom:16px; }}
    .pipeline-title {{ font-size:1.4rem; font-weight:800; color:#f6f8ff; }}
    .pipeline-copy {{ color:#8d98b8; margin-top:4px; }}
    .pipeline-score {{ font-size:2rem; font-weight:900; color:#8db0ff; }}
    .pipeline-bar {{ height:8px; border-radius:999px; background:#202844; overflow:hidden; margin-bottom:18px; }}
    .pipeline-bar-fill {{ width:100%; height:100%; background:linear-gradient(90deg,#4c7dff 0%,#7c5cff 100%); }}
    .pipeline-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .pipeline-chip {{ background:rgba(32,136,122,.12); border:1px solid rgba(72,182,158,.22); border-radius:16px; padding:12px; }}
    .chip-title {{ color:#9de3d3; font-weight:700; }}
    .chip-sub {{ color:#69849d; font-size:.82rem; margin-top:4px; }}
    .side {{ background:#0d1220; color:#eef2ff; padding:0; display:flex; height:100vh; position:sticky; top:0; border-left:1px solid rgba(149,166,214,.12); }}
    .side-card {{ width:100%; height:100vh; border:none; border-radius:0; background:linear-gradient(180deg,#0f1526 0%,#0a1020 100%); box-shadow:none; padding:0; display:grid; grid-template-rows:auto minmax(0,1fr) auto; overflow:hidden; }}
    .chat-header {{ padding:18px 18px 16px; border-bottom:1px solid rgba(149,166,214,.14); display:flex; align-items:center; gap:12px; }}
    .chat-icon {{ width:42px; height:42px; border-radius:14px; background:linear-gradient(135deg,#6e63ff 0%,#3d8cff 100%); display:grid; place-items:center; color:#fff; font-weight:800; box-shadow:0 12px 24px rgba(48,92,255,.24); }}
    .chat-title {{ font-size:1.02rem; font-weight:800; color:#f8faff; margin:0; }}
    .chat-subtitle {{ color:#7ee787; font-size:.82rem; }}
    .chat-badges {{ display:flex; flex-wrap:wrap; gap:8px; margin-left:auto; }}
    .chat-pill {{ display:inline-flex; align-items:center; gap:8px; min-height:28px; padding:0 10px; border-radius:999px; background:rgba(255,255,255,.06); border:1px solid rgba(149,166,214,.14); color:#c5d0ea; font-size:.76rem; font-weight:700; }}
    .chat-body {{ padding:18px; overflow:auto; display:grid; gap:14px; align-content:start; min-height:0; }}
    .chat-day {{ color:#7f8aa7; font-size:.76rem; text-transform:uppercase; letter-spacing:.08em; }}
    .chat-row {{ display:flex; gap:10px; align-items:flex-end; }}
    .chat-row.user {{ justify-content:flex-end; }}
    .chat-avatar {{ width:28px; height:28px; border-radius:10px; background:rgba(110,99,255,.16); border:1px solid rgba(110,99,255,.22); color:#b5bfff; display:grid; place-items:center; flex:0 0 auto; font-size:.78rem; }}
    .chat-bubble {{ max-width:82%; border-radius:20px; padding:14px 14px 10px; background:#151d31; border:1px solid rgba(149,166,214,.14); color:#e7ecfb; box-shadow:0 14px 24px rgba(0,0,0,.18); }}
    .chat-row.user .chat-bubble {{ background:linear-gradient(135deg,#3f82ff 0%,#5a6dff 100%); border-color:transparent; color:#fff; }}
    .chat-meta {{ margin-top:8px; color:#7f8aa7; font-size:.74rem; }}
    .chat-row.user .chat-meta {{ color:rgba(255,255,255,.72); }}
    .chat-composer-wrap {{ padding:14px 18px 20px; border-top:1px solid rgba(149,166,214,.14); background:rgba(9,14,26,.92); }}
    .chat-composer {{ display:grid; grid-template-columns:1fr auto; gap:10px; align-items:center; padding:10px; border-radius:18px; background:#12192b; border:1px solid rgba(149,166,214,.14); }}
    .chat-input {{ width:100%; min-height:22px; max-height:96px; resize:none; border:none; outline:none; background:transparent; color:#eef2ff; font:inherit; line-height:1.5; }}
    .chat-input::placeholder {{ color:#72809f; }}
    .chat-send {{ width:42px; height:42px; border:none; border-radius:14px; background:linear-gradient(135deg,#3f82ff 0%,#5a6dff 100%); color:#fff; display:grid; place-items:center; font-weight:900; }}
    .chat-send:disabled {{ opacity:.45; cursor:not-allowed; }}
    .hidden {{ display:none !important; }}
    .suggestion-btn {{ position:fixed; bottom:24px; left:12px; height:38px; padding:0 16px; border-radius:999px; background:linear-gradient(135deg,#f4c15d 0%,#f4903d 100%); border:none; color:#1a1200; font-size:.82rem; font-weight:800; display:none; align-items:center; gap:8px; box-shadow:0 8px 24px rgba(244,193,93,.35); z-index:100; cursor:pointer; white-space:nowrap; }}
    .suggestion-btn.visible {{ display:flex; }}
    .suggestion-btn .badge {{ min-width:18px; height:18px; padding:0 5px; border-radius:999px; background:rgba(0,0,0,.25); color:#fff; font-size:.65rem; font-weight:900; display:grid; place-items:center; }}
    .suggestion-panel {{ position:fixed; bottom:80px; left:12px; width:216px; background:#111827; border:1px solid rgba(244,193,93,.22); border-radius:20px; padding:14px; z-index:100; display:none; box-shadow:0 16px 40px rgba(0,0,0,.4); }}
    .suggestion-panel.open {{ display:block; }}
    .suggestion-panel-title {{ color:#f4c15d; font-size:.75rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; margin-bottom:10px; }}
    .suggestion-item {{ background:#1a2235; border:1px solid rgba(124,137,178,.14); border-radius:14px; padding:10px 12px; margin-bottom:8px; cursor:pointer; transition:border-color .15s; }}
    .suggestion-item:last-child {{ margin-bottom:0; }}
    .suggestion-item:hover {{ border-color:rgba(244,193,93,.4); }}
    .suggestion-item-title {{ color:#eef2ff; font-size:.84rem; font-weight:700; margin-bottom:3px; }}
    .suggestion-item-cat {{ font-size:.72rem; font-weight:700; padding:2px 8px; border-radius:999px; display:inline-block; }}
    .cat-content_quality {{ background:rgba(76,125,255,.15); color:#8db0ff; }}
    .cat-strategy_gap {{ background:rgba(52,211,153,.12); color:#5ce1b4; }}
    .cat-copy_optimization {{ background:rgba(244,193,93,.12); color:#f4c15d; }}
    .suggestion-chat-card {{ background:#1a2235; border:1px solid rgba(244,193,93,.2); border-radius:16px; padding:14px; margin-top:10px; }}
    .suggestion-chat-title {{ color:#f4c15d; font-weight:800; font-size:.9rem; margin-bottom:4px; }}
    .suggestion-chat-desc {{ color:#8d98b8; font-size:.84rem; margin-bottom:12px; }}
    .suggestion-actions {{ display:flex; gap:8px; }}
    .accept-btn {{ flex:1; min-height:36px; border:none; border-radius:10px; background:linear-gradient(135deg,#34d399 0%,#059669 100%); color:#fff; font-weight:800; font-size:.84rem; cursor:pointer; }}
    .decline-btn {{ flex:1; min-height:36px; border:none; border-radius:10px; background:rgba(239,68,68,.15); color:#f87171; font-weight:800; font-size:.84rem; cursor:pointer; border:1px solid rgba(239,68,68,.2); }}
    @media (max-width:1280px) {{ .app {{ grid-template-columns:240px 1fr; }} .side {{ grid-column:1 / -1; }} .main {{ border-right:none; }} .pipeline-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
    @media (max-width:900px) {{ .app {{ grid-template-columns:1fr; }} .sidebar {{ display:none; }} .pipeline-grid {{ grid-template-columns:1fr; }} .engine-card {{ flex-direction:column; align-items:flex-start; }} }}
  </style>
</head>
<body>
  <main class="app">
    <aside class="sidebar">
      <div class="logo"><div class="logo-mark">M</div><div>Marko AI</div></div>
      <div class="label">Orchestrator</div>
      <div class="nav">
        <button class="nav-item active" id="dashboard-nav" type="button"><div class="ic">CD</div><div>Creative Director</div></button>
      </div>
      <div class="label">Specialist Agents</div>
      <div class="nav">
        <button class="nav-item specialist" data-agent-tab="hooks" type="button"><div class="ic">HG</div><div>Hook Generator</div></button>
        <button class="nav-item specialist" data-agent-tab="angles" type="button"><div class="ic">AS</div><div>Angle Strategist</div></button>
        <button class="nav-item specialist" data-agent-tab="copy" type="button"><div class="ic">CA</div><div>Copy Architect</div></button>
        <button class="nav-item specialist" data-agent-tab="concepts" type="button"><div class="ic">VP</div><div>Visual Planner</div></button>
      </div>
      <div class="label">Analysis</div>
      <div class="nav"><a class="nav-item" href="/top-creatives"><div class="ic">EX</div><div>Execution History</div></a></div>
      <div class="user"><div class="avatar">JD</div><div><div style="font-weight:700;">John Doe</div><div style="color:#7b7b7b;font-size:.9rem;">Creative Ops</div></div></div>
    </aside>

    <button class="suggestion-btn" id="suggestion-btn" title="AI Suggestions">
      💡 Suggestions <span class="badge" id="suggestion-badge">0</span>
    </button>
    <div class="suggestion-panel" id="suggestion-panel">
      <div class="suggestion-panel-title">💡 AI Suggestions</div>
      <div id="suggestion-list"></div>
    </div>

    <section class="main">
      <section class="content">
        <div class="canvas">
          <div class="hero" id="hero-card">
            <h1 class="dashboard-title">Strategy Dashboard</h1>
            <p class="dashboard-subtitle">Generate and monitor your AI-powered creative strategy.</p>
            <div class="engine-card">
              <div>
                <div class="engine-title">AI Growth Strategy Engine</div>
                <div class="engine-copy">Run the full campaign pipeline to generate hooks, angles, scored copy, and visual concepts.</div>
              </div>
              <button id="hero-generate" class="engine-action" type="button">Generate Strategy</button>
            </div>
            <div class="brief-form">
              <div class="brief-grid">
                <div class="field">
                  <label class="field-label">Brand Name</label>
                  <input class="field-input" id="f-brand" type="text" placeholder="e.g. Marko AI" value="Marko AI">
                </div>
                <div class="field">
                  <label class="field-label">Platform</label>
                  <select class="field-input" id="f-platform">
                    <option value="meta">Meta</option>
                    <option value="google">Google</option>
                    <option value="tiktok">TikTok</option>
                  </select>
                </div>
                <div class="field">
                  <label class="field-label">Objective</label>
                  <select class="field-input" id="f-objective">
                    <option value="conversions">Conversions</option>
                    <option value="traffic">Traffic</option>
                    <option value="awareness">Awareness</option>
                  </select>
                </div>
                <div class="field">
                  <label class="field-label">Tone</label>
                  <select class="field-input" id="f-tone">
                    <option value="premium">Premium</option>
                    <option value="casual">Casual</option>
                    <option value="bold">Bold</option>
                    <option value="friendly">Friendly</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
                <div class="field span-2">
                  <label class="field-label">Product Description</label>
                  <textarea class="field-input field-ta" id="f-desc" placeholder="What does your product do?">AI ad tool that generates hooks, ad copy, platform-specific strategy, and creative directions for founders.</textarea>
                </div>
                <div class="field span-2">
                  <label class="field-label">Target Audience</label>
                  <input class="field-input" id="f-audience" type="text" placeholder="e.g. Startup founders running paid ads in-house" value="Startup founders and growth marketers who run paid acquisition in-house">
                </div>
                <div class="field span-2">
                  <label class="field-label">Key Benefits <span style="color:#667291;font-weight:400;">(comma separated)</span></label>
                  <input class="field-input" id="f-benefits" type="text" placeholder="e.g. Save time, Better CTR" value="Launch more ad variations in minutes, Generate sharper hooks for cold traffic">
                </div>
                <div class="field">
                  <label class="field-label">Competitors <span style="color:#667291;font-weight:400;">(comma separated)</span></label>
                  <input class="field-input" id="f-competitors" type="text" placeholder="e.g. Jasper, Copy.ai" value="Jasper, Copy.ai">
                </div>
                <div class="field">
                  <label class="field-label">Visual Style</label>
                  <input class="field-input" id="f-visual" type="text" placeholder="e.g. cinematic SaaS ads" value="cinematic SaaS ads with founder energy">
                </div>
              </div>
              <div class="count-grid">
                <div class="count-card">
                  <div class="count-label">Hooks</div>
                  <input class="count-input" id="f-hooks" type="number" value="10" min="10" max="20">
                </div>
                <div class="count-card">
                  <div class="count-label">Angles</div>
                  <input class="count-input" id="f-angles" type="number" value="3" min="3" max="6">
                </div>
                <div class="count-card">
                  <div class="count-label">Copy variants</div>
                  <input class="count-input" id="f-copy" type="number" value="5" min="5" max="10">
                </div>
                <div class="count-card">
                  <div class="count-label">Concepts</div>
                  <input class="count-input" id="f-concepts" type="number" value="2" min="1" max="4">
                </div>
              </div>
            </div>

          </div>

          <div class="loading-panel hidden" id="loading-panel">
            <div class="loading-shell">
              <div>
                <h2>Generating campaign</h2>
                <p>Your hooks, angles, ad copy, and concepts are being prepared now.</p>
                <div class="loading-dots" aria-hidden="true"><span></span><span></span><span></span></div>
              </div>
            </div>
          </div>

          <div class="results-panel hidden" id="results-panel">
            <div style="display:flex;justify-content:space-between;gap:14px;align-items:flex-start;flex-wrap:wrap;">
              <div><h2 id="results-title">Campaign Output</h2><div class="status-line" id="live-status">Ready.</div></div>
              <div class="tabs">
                <button class="tab active" data-tab="hooks" type="button">Hooks <span class="tab-count" id="hooks-count">0</span></button>
                <button class="tab" data-tab="angles" type="button">Angles <span class="tab-count" id="angles-count">0</span></button>
                <button class="tab" data-tab="copy" type="button">Copy <span class="tab-count" id="copy-count">0</span></button>
                <button class="tab" data-tab="concepts" type="button">Concepts <span class="tab-count" id="concepts-count">0</span></button>
              </div>
            </div>
            <div class="section-panel" id="tab-hooks">
              <div class="section-head"><div><h3>Generated Hooks</h3><div class="section-kicker">These are the generated hooks for this run.</div></div><div class="section-count" id="hooks-count-large">0</div></div>
              <div class="single-stack" id="hooks-output"></div>
            </div>
            <div class="section-panel hidden" id="tab-angles">
              <div class="section-head"><div><h3>Generated Angles</h3><div class="section-kicker">Messaging angles organized separately from hooks.</div></div><div class="section-count" id="angles-count-large">0</div></div>
              <div class="single-stack" id="angles-output"></div>
            </div>
            <div class="section-panel hidden" id="tab-copy">
              <div class="section-head"><div><h3>Generated Ad Copy</h3><div class="section-kicker">Copy variations with matching ranked assets beside them in each card.</div></div><div class="section-count" id="copy-count-large">0</div></div>
              <div class="single-stack" id="copy-output"></div>
            </div>
            <div class="section-panel hidden" id="tab-concepts">
              <div class="section-head"><div><h3>Generated Concepts</h3><div class="section-kicker">Visual concepts and media status in one compact section.</div></div><div class="section-count" id="concepts-count-large">0</div></div>
              <div class="single-stack" id="concepts-output"></div>
            </div>
          </div>
        </div>


      </section>
    </section>

    <aside class="side">
      <div class="side-card">
        <div class="chat-header">
          <div class="chat-icon">AI</div>
          <div>
            <div class="chat-title">AI Assistant</div>
            <div class="chat-subtitle">Online</div>
          </div>
          <div class="chat-badges">
            <span class="chat-pill">Groq {groq_status}</span>
            <span class="chat-pill">NanoBanana {nanobanana_status}</span>
          </div>
        </div>
        <div class="chat-body" id="chat-body">
          <div class="chat-day">Assistant Feed</div>
          <div class="chat-row">
            <div class="chat-avatar">AI</div>
            <div class="chat-bubble">
              <div>Hi! I'm your AI assistant. Ask me anything about Marko AI, creative generation, or how to use this tool.</div>
              <div class="chat-meta">Assistant</div>
            </div>
          </div>
        </div>
        <div class="chat-composer-wrap">
          <div class="chat-composer">
            <textarea id="chat-input" class="chat-input" rows="1" placeholder="Ask the AI assistant anything..."></textarea>
            <button id="chat-send" class="chat-send" type="button">&#9654;</button>
          </div>
        </div>
      </div>
    </aside>
  </main>

  <script>
    const samplePayload = {payload_text};
    const payloadInput = document.getElementById("payload");
    const chatBody = document.getElementById("chat-body");
    const chatInput = document.getElementById("chat-input");
    const chatSend = document.getElementById("chat-send");
    const dashboardNav = document.getElementById("dashboard-nav");
    const heroCard = document.getElementById("hero-card");
    const loadingPanel = document.getElementById("loading-panel");
    const resultsPanel = document.getElementById("results-panel");
    const liveStatus = document.getElementById("live-status");
    const hooksOutput = document.getElementById("hooks-output");
    const anglesOutput = document.getElementById("angles-output");
    const copyOutput = document.getElementById("copy-output");
    const conceptsOutput = document.getElementById("concepts-output");
    const resultsTitle = document.getElementById("results-title");
    const countTargets = {{
      hooks: [document.getElementById("hooks-count"), document.getElementById("hooks-count-large")],
      angles: [document.getElementById("angles-count"), document.getElementById("angles-count-large")],
      copy: [document.getElementById("copy-count"), document.getElementById("copy-count-large")],
      concepts: [document.getElementById("concepts-count"), document.getElementById("concepts-count-large")],
    }};
    const tabTitles = {{
      hooks: "Campaign Output",
      angles: "Campaign Output",
      copy: "Campaign Output",
      concepts: "Campaign Output",
    }};

    function e(v) {{
      return String(v).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
    }}
    function chatTime() {{
      return new Date().toLocaleTimeString([], {{ hour: "2-digit", minute: "2-digit" }});
    }}
    function appendChatMessage(role, text) {{
      const row = document.createElement("div");
      row.className = "chat-row" + (role === "user" ? " user" : "");
      const avatar = document.createElement("div");
      avatar.className = "chat-avatar";
      avatar.textContent = role === "user" ? "You" : "AI";
      const bubble = document.createElement("div");
      bubble.className = "chat-bubble";
      bubble.innerHTML = "<div>" + text + "</div><div class='chat-meta'>" + (role === "user" ? "You" : "Assistant") + " \u2022 " + chatTime() + "</div>";
      row.appendChild(avatar);
      row.appendChild(bubble);
      chatBody.appendChild(row);
      chatBody.scrollTop = chatBody.scrollHeight;
    }}
    let chatContext = {{}};
    async function sendChatMessage() {{
      const message = chatInput.value.trim();
      if (!message) return;
      appendChatMessage("user", e(message));
      chatInput.value = "";
      chatSend.disabled = true;
      appendChatMessage("ai", "<span class='loading-dots'><span></span><span></span><span></span></span>");
      try {{
        const res = await fetch("/chat-assistant", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ message, context: chatContext }}),
        }});
        const data = await res.json();
        const loading = chatBody.querySelector(".chat-row:last-child");
        if (loading) loading.remove();
        appendChatMessage("ai", e(data.reply));
        chatContext = data.context || {{}};
      }} catch (err) {{
        const loading = chatBody.querySelector(".chat-row:last-child");
        if (loading) loading.remove();
        appendChatMessage("ai", "Sorry, there was an error contacting the assistant.");
      }} finally {{
        chatSend.disabled = false;
      }}
    }}
    chatSend.addEventListener("click", sendChatMessage);
    chatInput.addEventListener("keydown", (event) => {{
      if (event.key === "Enter" && !event.shiftKey) {{
        event.preventDefault();
        sendChatMessage();
      }}
    }});
    function setStatus(msg, bad = false) {{
      liveStatus.textContent = msg;
      liveStatus.style.color = bad ? "#b42318" : "#586173";
    }}
    function showLoading() {{
      heroCard.classList.add("hidden");
      loadingPanel.classList.remove("hidden");
      resultsPanel.classList.add("hidden");
    }}
    function showResults() {{
      heroCard.classList.add("hidden");
      loadingPanel.classList.add("hidden");
      resultsPanel.classList.remove("hidden");
    }}
    function resetOutputs() {{
      empty(hooksOutput, "Hooks will appear here after generation.");
      empty(anglesOutput, "Angles will appear here after generation.");
      empty(copyOutput, "Ad copy will appear here after generation.");
      empty(conceptsOutput, "Generated concepts will appear here after generation.");
      setCount("hooks", 0);
      setCount("angles", 0);
      setCount("copy", 0);
      setCount("concepts", 0);
    }}
    function empty(target, msg) {{
      target.innerHTML = "<div class='card'><p>" + e(msg) + "</p></div>";
    }}
    function setCount(key, value) {{
      (countTargets[key] || []).forEach((node) => {{
        if (node) node.textContent = String(value);
      }});
    }}
    function activateTab(current) {{
      document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === current));
      document.getElementById("tab-hooks").classList.toggle("hidden", current !== "hooks");
      document.getElementById("tab-angles").classList.toggle("hidden", current !== "angles");
      document.getElementById("tab-copy").classList.toggle("hidden", current !== "copy");
      document.getElementById("tab-concepts").classList.toggle("hidden", current !== "concepts");
      document.querySelectorAll(".specialist").forEach((item) => item.classList.toggle("active", item.dataset.agentTab === current));
      dashboardNav.classList.remove("active");
      resultsTitle.textContent = tabTitles[current] || "Generated Content";
    }}
    function showDashboard() {{
      heroCard.classList.remove("hidden");
      loadingPanel.classList.add("hidden");
      resultsPanel.classList.add("hidden");
      dashboardNav.classList.add("active");
      document.querySelectorAll(".specialist").forEach((item) => item.classList.remove("active"));
    }}
    function list(target, items, render) {{
      if (!items || !items.length) {{
        empty(target, "No items.");
        return;
      }}
      target.innerHTML = items.map(render).join("");
    }}
    function renderAll(data) {{
      showResults();
      activateTab("hooks");
      const hooks = data.hooks || [];
      const angles = data.angles || [];
      const copies = [...(data.ad_copies || [])].sort((a, b) => (b.total_score ?? -1) - (a.total_score ?? -1));
      const concepts = data.visual_concepts || [];
      const generated = data.generated_creatives || [];
      setCount("hooks", hooks.length);
      setCount("angles", angles.length);
      setCount("copy", copies.length);
      setCount("concepts", concepts.length);
      chatContext = {{ ...chatContext, campaign: {{ hooks, angles, copies, concepts }} }};
      fetchSuggestions({{ hooks, angles, copies, concepts }});
      list(hooksOutput, hooks, (x) => "<div class='card'><h3>" + e(x.type) + "</h3><p>" + e(x.text) + "</p><p>" + e(x.rationale) + "</p></div>");
      list(anglesOutput, angles, (x) => "<div class='card'><h3>" + e(x.name) + "</h3><p>" + e(x.description) + "</p><p>Emotion: " + e(x.target_emotion) + " | Use case: " + e(x.use_case) + "</p></div>");
      list(copyOutput, copies, (x) => "<div class='card'><h3>" + e(x.headline) + "</h3><p>" + e(x.primary_text) + "</p><p>CTA: " + e(x.cta) + " | Hook: " + e(x.hook_text) + "</p><div class='mono'>Score: " + e(x.total_score ?? "-") + " | Rank: " + e(x.score_rank ?? "-") + " | Angle: " + e(x.angle_name) + "</div>" + (x.score_rationale ? "<div class='mono'>" + e(x.score_rationale) + "</div>" : "") + "</div>");
      list(conceptsOutput, concepts, (x) => {{
        const gen = generated.find((item) => item.concept_id === x.concept_id);
        return "<div class='card'><h3>" + e(x.concept_id) + " | " + e(x.aspect_ratio) + " | " + e(x.media_type) + "</h3><p>" + e(x.scene_description) + "</p><div class='mono'>" + e(x.generation_prompt) + "</div>" + (gen ? "<div class='mono'>Media: " + e(gen.status) + (gen.error ? " | " + e(gen.error) : "") + "</div>" : "") + "</div>";
      }});
    }}

    document.getElementById("hero-generate").addEventListener("click", async () => {{
      const payload = {{
        brand_name: document.getElementById("f-brand").value.trim(),
        product_description: document.getElementById("f-desc").value.trim(),
        target_audience: document.getElementById("f-audience").value.trim(),
        platform: document.getElementById("f-platform").value,
        objective: document.getElementById("f-objective").value,
        tone: document.getElementById("f-tone").value,
        key_benefits: document.getElementById("f-benefits").value.split(",").map(s => s.trim()).filter(Boolean),
        competitors: document.getElementById("f-competitors").value.split(",").map(s => s.trim()).filter(Boolean),
        visual_style: document.getElementById("f-visual").value.trim(),
        hook_count: parseInt(document.getElementById("f-hooks").value) || 10,
        angle_count: parseInt(document.getElementById("f-angles").value) || 3,
        copy_count: parseInt(document.getElementById("f-copy").value) || 5,
        concept_count: parseInt(document.getElementById("f-concepts").value) || 2,
      }};
      if (!payload.brand_name || !payload.product_description) {{
        alert("Please fill in at least Brand Name and Product Description.");
        return;
      }}
      resetOutputs();
      showLoading();
      setStatus("Generating campaign...");
      try {{
        const response = await fetch("/generate-creatives", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Request failed.");
        renderAll(data);
        setStatus("Generation complete.");
      }} catch (error) {{
        setStatus(error.message || "Generation failed.", true);
        showDashboard();
      }}
    }});
    dashboardNav.addEventListener("click", () => {{
      showDashboard();
      setStatus("Strategy dashboard ready.");
    }});
    document.querySelectorAll(".tab").forEach((tab) => {{
      tab.addEventListener("click", () => {{
        activateTab(tab.dataset.tab);
      }});
    }});
    document.querySelectorAll(".specialist").forEach((item) => {{
      item.addEventListener("click", () => {{
        showResults();
        activateTab(item.dataset.agentTab);
      }});
    }});
    // SUGGESTIONS
    const suggestionBtn = document.getElementById("suggestion-btn");
    const suggestionPanel = document.getElementById("suggestion-panel");
    const suggestionList = document.getElementById("suggestion-list");
    const suggestionBadge = document.getElementById("suggestion-badge");
    let currentSuggestions = [];
    let activeSuggestion = null;

    suggestionBtn.addEventListener("click", () => {{
      suggestionPanel.classList.toggle("open");
    }});

    document.addEventListener("click", (e) => {{
      if (!suggestionPanel.contains(e.target) && e.target !== suggestionBtn) {{
        suggestionPanel.classList.remove("open");
      }}
    }});

    async function fetchSuggestions(campaign) {{
      try {{
        const res = await fetch("/suggestions", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ campaign }}),
        }});
        const data = await res.json();
        currentSuggestions = data.suggestions || [];
        suggestionBadge.textContent = currentSuggestions.length;
        suggestionBtn.classList.add("visible");
        renderSuggestionList();
      }} catch (e) {{
        console.error("Suggestions failed:", e);
      }}
    }}

    function renderSuggestionList() {{
      suggestionList.innerHTML = currentSuggestions.map((s) => `
        <div class="suggestion-item" onclick="openSuggestion('${{s.id}}')">
          <div class="suggestion-item-title">${{e(s.title)}}</div>
          <span class="suggestion-item-cat cat-${{s.category}}">${{e(s.category.replace("_"," "))}}</span>
        </div>
      `).join("");
    }}

    function openSuggestion(id) {{
      activeSuggestion = currentSuggestions.find((s) => s.id === id);
      if (!activeSuggestion) return;
      suggestionPanel.classList.remove("open");

      // inject suggestion card into chat
      const existing = document.getElementById("active-suggestion-card");
      if (existing) existing.remove();

      const card = document.createElement("div");
      card.id = "active-suggestion-card";
      card.className = "chat-row";
      card.innerHTML = `
        <div class="chat-avatar">💡</div>
        <div class="chat-bubble" style="max-width:90%;background:#1a2235;border-color:rgba(244,193,93,.2);">
          <div class="suggestion-chat-card">
            <div class="suggestion-chat-title">${{e(activeSuggestion.title)}}</div>
            <div class="suggestion-chat-desc">${{e(activeSuggestion.description)}}</div>
            <div class="suggestion-actions">
              <button class="accept-btn" onclick="executeSuggestion()">✓ Accept</button>
              <button class="decline-btn" onclick="declineSuggestion()">✕ Decline</button>
            </div>
          </div>
          <div class="chat-meta">Suggestion • now</div>
        </div>
      `;
      chatBody.appendChild(card);
      chatBody.scrollTop = chatBody.scrollHeight;
    }}

    function declineSuggestion() {{
      const card = document.getElementById("active-suggestion-card");
      if (card) {{
        card.querySelector(".suggestion-actions").innerHTML = "<span style='color:#f87171;font-size:.84rem;font-weight:700;'>Declined</span>";
      }}
      activeSuggestion = null;
    }}

    async function executeSuggestion() {{
      if (!activeSuggestion) return;
      const card = document.getElementById("active-suggestion-card");
      if (card) {{
        card.querySelector(".suggestion-actions").innerHTML = "<span style='color:#f4c15d;font-size:.84rem;font-weight:700;'>Executing...</span>";
      }}

      try {{
        const res = await fetch("/execute-suggestion", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ suggestion: activeSuggestion, campaign: chatContext.campaign || {{}} }}),
        }});
        const data = await res.json();

        // update UI based on action type
        if (data.updated_items && data.updated_items.length > 0) {{
          data.updated_items.forEach((item) => {{
            if (item.type === "hook") {{
              const x = item.data;
              const el = document.createElement("div");
              el.className = "card";
              el.style.border = "1px solid rgba(244,193,93,.3)";
              el.innerHTML = "<h3>" + e(x.type) + " <span style='color:#f4c15d;font-size:.75rem;'>NEW</span></h3><p>" + e(x.text) + "</p><p>" + e(x.rationale) + "</p>";
              hooksOutput.prepend(el);
              activateTab("hooks");
              showResults();
            }} else if (item.type === "angle") {{
              const x = item.data;
              const el = document.createElement("div");
              el.className = "card";
              el.style.border = "1px solid rgba(244,193,93,.3)";
              el.innerHTML = "<h3>" + e(x.name) + " <span style='color:#f4c15d;font-size:.75rem;'>NEW</span></h3><p>" + e(x.description) + "</p><p>Emotion: " + e(x.target_emotion) + " | Use case: " + e(x.use_case) + "</p>";
              anglesOutput.prepend(el);
              activateTab("angles");
              showResults();
            }} else if (item.type === "copy") {{
              const x = item.data;
              const el = document.createElement("div");
              el.className = "card";
              el.style.border = "1px solid rgba(244,193,93,.3)";
              el.innerHTML = "<h3>" + e(x.headline) + " <span style='color:#f4c15d;font-size:.75rem;'>UPDATED</span></h3><p>" + e(x.primary_text) + "</p><p>CTA: " + e(x.cta) + "</p><div class='mono'>Score: " + e(x.total_score ?? "-") + "</div>";
              copyOutput.prepend(el);
              activateTab("copy");
              showResults();
            }}
          }});
        }}

        if (card) {{
          card.querySelector(".suggestion-actions").innerHTML = "<span style='color:#34d399;font-size:.84rem;font-weight:700;'>✓ Done — " + e(data.message) + "</span>";
        }}

        // remove from suggestion list
        currentSuggestions = currentSuggestions.filter((s) => s.id !== activeSuggestion.id);
        suggestionBadge.textContent = currentSuggestions.length;
        renderSuggestionList();
        activeSuggestion = null;

      }} catch (err) {{
        if (card) {{
          card.querySelector(".suggestion-actions").innerHTML = "<span style='color:#f87171;font-size:.84rem;'>Execution failed.</span>";
        }}
      }}
    }}
  </script>
</body>
</html>"""