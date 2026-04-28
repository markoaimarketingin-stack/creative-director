// Configuration: Change this to your Render backend URL if hosting frontend on Vercel
// Example: const API_BASE_URL = "https://your-app.onrender.com";
let API_BASE_URL = (
  window.__APP_CONFIG__ &&
  typeof window.__APP_CONFIG__.BACKEND_URL === "string" &&
  window.__APP_CONFIG__.BACKEND_URL.trim()
)
  ? window.__APP_CONFIG__.BACKEND_URL.trim().replace(/\/+$/, "")
  : "";

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
const sampleInput = byId("f-samples");
const sampleHint = byId("f-samples-hint");
const btnChatHistory = byId("btn-chat-history");
const btnChatNew = byId("btn-chat-new");
const btnSidebarChat = byId("btn-sidebar-chat");
const chatHistoryPanel = byId("chat-history-panel");
const chatSessionsList = byId("chat-sessions-list");
const chatPanel = document.querySelector(".chat-panel");
const historyPanel = byId("history-panel");
const navExecutionHistory = byId("nav-execution-history");
const historyOutput = byId("history-output");

const MAX_SAMPLE_IMAGES = 4;
const MAX_SAMPLE_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;

const countTargets = {
  hooks: [byId("hooks-count"), byId("hooks-count-large")],
  angles: [byId("angles-count"), byId("angles-count-large")],
  copy: [byId("copy-count"), byId("copy-count-large")],
  concepts: [byId("concepts-count"), byId("concepts-count-large")]
};

let chatContext = {};
let chatSessionId = localStorage.getItem("chat_session_id");

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

function setSampleHint(message, bad = false) {
  if (!sampleHint) return;
  sampleHint.textContent = message;
  sampleHint.style.color = bad ? "#b42318" : "#575757";
}

function showDashboard() {
  heroCard.classList.remove("hidden");
  loadingPanel.classList.add("hidden");
  resultsPanel.classList.add("hidden");
  if (historyPanel) historyPanel.classList.add("hidden");
  dashboardNav.classList.add("active");
  document.querySelectorAll(".specialist").forEach((n) => n.classList.remove("active"));
  if (navExecutionHistory) navExecutionHistory.classList.remove("active");
}

function showLoading() {
  heroCard.classList.add("hidden");
  loadingPanel.classList.remove("hidden");
  resultsPanel.classList.add("hidden");
  if (historyPanel) historyPanel.classList.add("hidden");
}

function showResults() {
  heroCard.classList.add("hidden");
  loadingPanel.classList.add("hidden");
  resultsPanel.classList.remove("hidden");
  if (historyPanel) historyPanel.classList.add("hidden");
}

function showHistory() {
  heroCard.classList.add("hidden");
  loadingPanel.classList.add("hidden");
  resultsPanel.classList.add("hidden");
  if (historyPanel) historyPanel.classList.remove("hidden");
  
  dashboardNav.classList.remove("active");
  document.querySelectorAll(".specialist").forEach((n) => n.classList.remove("active"));
  if (navExecutionHistory) navExecutionHistory.classList.add("active");
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
    const res = await fetch(`${API_BASE_URL}/chat-assistant`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, context: chatContext, session_id: chatSessionId })
    });
    const data = await res.json();
    appendChat("ai", esc(data.reply || "No response received."));
    chatContext = data.context || chatContext;
    if (data.session_id && data.session_id !== chatSessionId) {
      chatSessionId = data.session_id;
      localStorage.setItem("chat_session_id", chatSessionId);
    }
  } catch {
    appendChat("ai", "Sorry, there was an error contacting the assistant.");
  } finally {
    chatSend.disabled = false;
  }
}

async function loadChatHistory() {
  if (!chatSessionId) return;
  try {
    const res = await fetch(`${API_BASE_URL}/chat-history/${chatSessionId}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.history && data.history.length > 0) {
      // Clear the chat body so we don't have duplicate default messages
      chatBody.innerHTML = '';
      data.history.forEach(msg => {
        appendChat(msg.role === "assistant" ? "ai" : "user", esc(msg.content));
      });
      // Pre-fill history into context
      chatContext.history = data.history;
    }
  } catch (e) {
    console.error("Failed to load chat history:", e);
  }
}

async function loadUiConfig() {
  try {
    const res = await fetch(`${API_BASE_URL}/ui-config`);
    const data = await res.json();
    document.title = data.app_name || "Creative Director Engine";
    if (!API_BASE_URL && data.backend_url && typeof data.backend_url === "string") {
      API_BASE_URL = data.backend_url.replace(/\/+$/, "");
    }
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

  if (navExecutionHistory) {
    navExecutionHistory.addEventListener("click", async () => {
      showHistory();
      empty(historyOutput, "Loading execution history...");
      try {
        const res = await fetch(`${API_BASE_URL}/top-creatives`);
        if (!res.ok) throw new Error("Failed to load history");
        const data = await res.json();
        
        if (!data.items || data.items.length === 0) {
          empty(historyOutput, "No previous executions found.");
          return;
        }

        historyOutput.innerHTML = data.items.map(item => {
          const imgs = (item.image_urls || []).map(url => `<img src="${url}" class="concept-img" alt="Creative image">`).join("");
          return `
            <div class="card">
              <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <h3 style="margin:0">${esc(item.campaign_name)}</h3>
                <span class="mono">Score: ${esc(item.total_score)}</span>
              </div>
              <p style="margin:5px 0;"><strong>Headline:</strong> ${esc(item.headline)}</p>
              <p style="margin:5px 0;"><strong>CTA:</strong> ${esc(item.cta)}</p>
              <div class="mono" style="margin-bottom: 10px;">Platform: ${esc(item.platform)} | Concept: ${esc(item.concept_id)}</div>
              ${imgs}
            </div>
          `;
        }).join("");
      } catch (e) {
        empty(historyOutput, "Error loading execution history.");
      }
    });
  }

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

      const sampleFiles = sampleInput ? sampleInput.files : [];
    if (sampleFiles.length > 0) {
        setStatus("Processing upload images...");
        const selected = Array.from(sampleFiles).slice(0, MAX_SAMPLE_IMAGES);
        for (const file of selected) {
          try {
            if (!file.type.startsWith("image/")) {
              continue;
            }
            if (file.size > MAX_SAMPLE_IMAGE_SIZE_BYTES) {
              continue;
            }
            const b64 = await getBase64(file);
            payload.sample_images.push(b64);
          } catch (e) {
            console.error("Error reading file", e);
          }
        }

        setSampleHint(
          payload.sample_images.length
          ? `Using ${payload.sample_images.length} reference image(s) for generation.`
          : "No valid sample images selected. Using text-only generation.",
          payload.sample_images.length === 0
        );
    }

    if (!payload.brand_name || !payload.product_description) {
      alert("Please fill in at least Brand Name and Product Description.");
      return;
    }

    resetOutputs();
    showLoading();
    setStatus("Generating campaign...");

    try {
      const response = await fetch(`${API_BASE_URL}/generate-creatives`, {
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

  if (sampleInput) {
    sampleInput.addEventListener("change", () => {
      const files = Array.from(sampleInput.files || []);
      if (!files.length) {
        setSampleHint("Optional. Up to 4 images, max 5MB each, used as visual references for Vertex AI.");
        return;
      }

      if (files.length > MAX_SAMPLE_IMAGES) {
        setSampleHint(`Selected ${files.length} files. Only first ${MAX_SAMPLE_IMAGES} will be used.`, true);
        return;
      }

      const oversized = files.some((f) => f.size > MAX_SAMPLE_IMAGE_SIZE_BYTES);
      if (oversized) {
        setSampleHint("One or more images are larger than 5MB and will be ignored.", true);
        return;
      }

      const invalidType = files.some((f) => !f.type.startsWith("image/"));
      if (invalidType) {
        setSampleHint("Only image files are accepted.", true);
        return;
      }

      setSampleHint(`Selected ${files.length} sample image(s).`);
    });
  }

  if (btnChatHistory) {
    btnChatHistory.addEventListener("click", async () => {
      chatHistoryPanel.classList.toggle("hidden");
      if (!chatHistoryPanel.classList.contains("hidden")) {
        chatSessionsList.innerHTML = '<div style="padding: 10px;">Loading...</div>';
        try {
          const res = await fetch(`${API_BASE_URL}/chat-sessions`);
          if (!res.ok) {
            chatSessionsList.innerHTML = `<div style="padding: 10px;">Error loading sessions (Status: ${res.status}). Ensure API is running.</div>`;
            return;
          }
          const data = await res.json();
          if (data.sessions && data.sessions.length > 0) {
            const validSessions = data.sessions.filter(s => s.session_id);
            if (validSessions.length > 0) {
              chatSessionsList.innerHTML = validSessions.map(s => {
                const title = s.title ? s.title : 'Session: ' + String(s.session_id).substring(0, 8);
                return `<div class="chat-session-item" data-id="${s.session_id}" style="padding: 10px; border-bottom: 1px solid #e5e5e5; cursor: pointer; font-size: 0.9em;">
                  <strong>${esc(title)}</strong><br>
                  <span style="font-size: 0.8em; color: #666;">${new Date(s.last_activity).toLocaleString()}</span>
                </div>`;
              }).join('');
              
              document.querySelectorAll('.chat-session-item').forEach(item => {
                item.addEventListener('click', () => {
                  chatSessionId = item.dataset.id;
                  localStorage.setItem("chat_session_id", chatSessionId);
                  chatHistoryPanel.classList.add("hidden");
                  loadChatHistory();
                });
              });
            } else {
              chatSessionsList.innerHTML = '<div style="padding: 10px;">No previous chats found.</div>';
            }
          } else {
            chatSessionsList.innerHTML = '<div style="padding: 10px;">No previous chats found.</div>';
          }
        } catch (e) {
          chatSessionsList.innerHTML = '<div style="padding: 10px;">Error loading sessions.</div>';
        }
      }
    });
  }

  if (btnChatNew) {
    btnChatNew.addEventListener("click", () => {
      chatSessionId = null;
      localStorage.removeItem("chat_session_id");
      chatContext.history = [];
      chatBody.innerHTML = `
        <div class="chat-row">
          <div class="chat-avatar">AI</div>
          <div class="chat-bubble">
            Hi! I am the Creative Director Assistant. I can help with hooks, angles, copy, concepts, and campaign strategy.
            <div class="meta">Assistant</div>
          </div>
          <div class="chat-time">Just now</div>
        </div>
      `;
      if (chatHistoryPanel) chatHistoryPanel.classList.add("hidden");
    });
  }

  if (btnSidebarChat && chatPanel) {
    btnSidebarChat.addEventListener("click", () => {
      chatPanel.classList.remove("hidden");
    });
  }

}

resetOutputs();
wireEvents();
loadUiConfig();
loadChatHistory();
