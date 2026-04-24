const byId = (id) => document.getElementById(id);
const chatBody = byId("chat-body");
const chatInput = byId("chat-input");
const chatSend = byId("chat-send");
const dashboardNav = byId("dashboard-nav");
const heroCard = byId("hero-card");
const loadingPanel = byId("loading-panel");
const resultsPanel = byId("results-panel");
const liveStatus = byId("live-status");
const resultsTitle = byId("results-title");
const hooksOutput = byId("hooks-output");
const anglesOutput = byId("angles-output");
const copyOutput = byId("copy-output");
const conceptsOutput = byId("concepts-output");

const countTargets = {
  hooks: [byId("hooks-count"), byId("hooks-count-large")],
  angles: [byId("angles-count"), byId("angles-count-large")],
  copy: [byId("copy-count"), byId("copy-count-large")],
  concepts: [byId("concepts-count"), byId("concepts-count-large")]
};

let chatContext = {};

function esc(v) {
  return String(v)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(msg, bad = false) {
  liveStatus.textContent = msg;
  liveStatus.style.color = bad ? "#b42318" : "#575757";
}

async function getBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });
}

function showDashboard() {
  heroCard.classList.remove("hidden");
  loadingPanel.classList.add("hidden");
  resultsPanel.classList.add("hidden");
  dashboardNav.classList.add("active");
  document.querySelectorAll(".specialist").forEach((n) => n.classList.remove("active"));
}

function showLoading() {
  heroCard.classList.add("hidden");
  loadingPanel.classList.remove("hidden");
  resultsPanel.classList.add("hidden");
}

function showResults() {
  heroCard.classList.add("hidden");
  loadingPanel.classList.add("hidden");
  resultsPanel.classList.remove("hidden");
}

function setCount(key, value) {
  (countTargets[key] || []).forEach((n) => {
    if (n) n.textContent = String(value);
  });
}

function empty(target, msg) {
  target.innerHTML = `<div class="card"><p>${esc(msg)}</p></div>`;
}

function resetOutputs() {
  empty(hooksOutput, "Hooks will appear here after generation.");
  empty(anglesOutput, "Angles will appear here after generation.");
  empty(copyOutput, "Ad copy will appear here after generation.");
  empty(conceptsOutput, "Generated concepts will appear here after generation.");
  setCount("hooks", 0);
  setCount("angles", 0);
  setCount("copy", 0);
  setCount("concepts", 0);
}

function activateTab(tab) {
  document.querySelectorAll(".tab").forEach((n) => n.classList.toggle("active", n.dataset.tab === tab));
  byId("tab-hooks").classList.toggle("hidden", tab !== "hooks");
  byId("tab-angles").classList.toggle("hidden", tab !== "angles");
  byId("tab-copy").classList.toggle("hidden", tab !== "copy");
  byId("tab-concepts").classList.toggle("hidden", tab !== "concepts");
  document.querySelectorAll(".specialist").forEach((n) => n.classList.toggle("active", n.dataset.agentTab === tab));
  dashboardNav.classList.remove("active");
  resultsTitle.textContent = "Campaign Output";
}

function list(target, items, render) {
  if (!items || !items.length) {
    empty(target, "No items.");
    return;
  }
  target.innerHTML = items.map(render).join("");
}

function renderAll(data) {
  showResults();
  activateTab("hooks");

  const hooks = data.hooks || [];
  const angles = data.angles || [];
  const copies = [...(data.ad_copies || [])].sort((a, b) => (b.total_score ?? -1) - (a.total_score ?? -1));
  const concepts = data.visual_concepts || [];
  const generated = data.generated_creatives || [];
  const genMap = generated.reduce((acc, x) => ({ ...acc, [x.concept_id]: x }), {});

  setCount("hooks", hooks.length);
  setCount("angles", angles.length);
  setCount("copy", copies.length);
  setCount("concepts", concepts.length);

  chatContext = { ...chatContext, campaign: { hooks, angles, copies, concepts } };

  list(hooksOutput, hooks, (x) => `<div class="card"><h3>${esc(x.type)}</h3><p>${esc(x.text)}</p><p>${esc(x.rationale)}</p></div>`);
  list(anglesOutput, angles, (x) => `<div class="card"><h3>${esc(x.name)}</h3><p>${esc(x.description)}</p><p>Emotion: ${esc(x.target_emotion)} | Use case: ${esc(x.use_case)}</p></div>`);
  list(copyOutput, copies, (x) => `<div class="card"><h3>${esc(x.headline)}</h3><p>${esc(x.primary_text)}</p><p>CTA: ${esc(x.cta)} | Hook: ${esc(x.hook_text)}</p><div class="mono">Score: ${esc(x.total_score ?? "-")} | Rank: ${esc(x.score_rank ?? "-")} | Angle: ${esc(x.angle_name)}</div></div>`);
  list(conceptsOutput, concepts, (x) => {
    const gen = genMap[x.concept_id] || {};
    const imgs = (gen.image_urls || []).map(url => `<img src="${url}" class="concept-img" alt="Generated concept" onerror="this.style.display='none'">`).join("");
    const error = gen.error ? `<div class="error-msg">Error: ${esc(gen.error)}</div>` : "";
    
    return `
      <div class="card">
        <h3>${esc(x.concept_id)} | ${esc(x.aspect_ratio)} | ${esc(x.media_type)}</h3>
        ${imgs}
        ${error}
        <p>${esc(x.scene_description)}</p>
        <div class="mono">${esc(x.generation_prompt)}</div>
      </div>
    `;
  });
}

function appendChat(role, text) {
  const row = document.createElement("div");
  row.className = "chat-row" + (role === "user" ? " user" : "");
  row.innerHTML = `<div class="chat-avatar">${role === "user" ? "You" : "AI"}</div><div class="chat-bubble">${text}<div class="meta">${role === "user" ? "You" : "Assistant"}</div></div>`;
  chatBody.appendChild(row);
  chatBody.scrollTop = chatBody.scrollHeight;
}

async function sendChatMessage() {
  const message = chatInput.value.trim();
  if (!message) return;
  appendChat("user", esc(message));
  chatInput.value = "";
  chatSend.disabled = true;

  try {
    const res = await fetch("/chat-assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, context: chatContext })
    });
    const data = await res.json();
    appendChat("ai", esc(data.reply || "No response received."));
    chatContext = data.context || chatContext;
  } catch {
    appendChat("ai", "Sorry, there was an error contacting the assistant.");
  } finally {
    chatSend.disabled = false;
  }
}

async function loadUiConfig() {
  try {
    const res = await fetch("/ui-config");
    const data = await res.json();
    document.title = data.app_name || "Creative Director Engine";
  } catch {
    document.title = "Creative Director Engine";
  }
}

function wireEvents() {
  chatSend.addEventListener("click", sendChatMessage);
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  dashboardNav.addEventListener("click", () => {
    showDashboard();
    setStatus("Strategy dashboard ready.");
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => activateTab(tab.dataset.tab));
  });

  document.querySelectorAll(".specialist").forEach((item) => {
    item.addEventListener("click", () => {
      showResults();
      activateTab(item.dataset.agentTab);
    });
  });

  byId("hero-generate").addEventListener("click", async () => {
    const payload = {
      brand_name: byId("f-brand").value.trim(),
      product_description: byId("f-desc").value.trim(),
      target_audience: byId("f-audience").value.trim(),
      platform: byId("f-platform").value,
      objective: byId("f-objective").value,
      tone: byId("f-tone").value,
      key_benefits: byId("f-benefits").value.split(",").map((s) => s.trim()).filter(Boolean),
      competitors: byId("f-competitors").value.split(",").map((s) => s.trim()).filter(Boolean),
      visual_style: byId("f-visual").value.trim(),
      hook_count: parseInt(byId("f-hooks").value, 10) || 10,
      angle_count: parseInt(byId("f-angles").value, 10) || 3,
      copy_count: parseInt(byId("f-copy").value, 10) || 5,
      concept_count: parseInt(byId("f-concepts").value, 10) || 2,
      sample_images: []
    };

    const sampleFiles = byId("f-samples").files;
    if (sampleFiles.length > 0) {
        setStatus("Processing upload images...");
        for (const file of sampleFiles) {
            try {
                const b64 = await getBase64(file);
                payload.sample_images.push(b64);
            } catch (e) {
                console.error("Error reading file", e);
            }
        }
    }

    if (!payload.brand_name || !payload.product_description) {
      alert("Please fill in at least Brand Name and Product Description.");
      return;
    }

    resetOutputs();
    showLoading();
    setStatus("Generating campaign...");

    try {
      const response = await fetch("/generate-creatives", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed.");
      renderAll(data);
      setStatus("Generation complete.");
    } catch (error) {
      setStatus(error.message || "Generation failed.", true);
      showDashboard();
    }
  });

}

resetOutputs();
wireEvents();
loadUiConfig();
