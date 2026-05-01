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
const heroGenerateButton = byId("hero-generate");
const hooksOutput = byId("hooks-output");
const anglesOutput = byId("angles-output");
const copyOutput = byId("copy-output");
const conceptsOutput = byId("concepts-output");
const finalsOutput = byId("finals-output");
const previewsOutput = byId("previews-output");
const exportsOutput = byId("exports-output");
const sampleInput = byId("f-samples");
const sampleHint = byId("f-samples-hint");
const logoInput = byId("f-logo");
const btnChatHistory = byId("btn-chat-history");
const btnChatNew = byId("btn-chat-new");
const btnSidebarChat = byId("btn-sidebar-chat");
const chatHistoryPanel = byId("chat-history-panel");
const chatSessionsList = byId("chat-sessions-list");
const chatPanel = document.querySelector(".chat-panel");
const historyPanel = byId("history-panel");
const navExecutionHistory = byId("nav-execution-history");
const historyOutput = byId("history-output");
const requiredFieldIds = ["f-brand", "f-desc", "f-audience", "f-benefits"];

const MAX_SAMPLE_IMAGES = 4;
const MAX_SAMPLE_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;

const countTargets = {
  finals: [byId("finals-count"), byId("finals-count-large")],
  previews: [byId("previews-count"), byId("previews-count-large")],
  hooks: [byId("hooks-count"), byId("hooks-count-large")],
  angles: [byId("angles-count"), byId("angles-count-large")],
  copy: [byId("copy-count"), byId("copy-count-large")],
  concepts: [byId("concepts-count"), byId("concepts-count-large")],
  exports: [byId("exports-count"), byId("exports-count-large")]
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
  liveStatus.style.color = bad ? "#a9342a" : "#4f5f72";
}

function clearFieldErrors() {
  requiredFieldIds.forEach((id) => {
    const field = byId(id);
    if (field) field.classList.remove("field-error");
  });
}

function markFieldError(id) {
  const field = byId(id);
  if (field) field.classList.add("field-error");
}

function validatePayload(payload) {
  clearFieldErrors();
  const errors = [];
  if (!payload.brand_name) {
    errors.push("Brand Name is required.");
    markFieldError("f-brand");
  }
  if (!payload.product_description) {
    errors.push("Product Description is required.");
    markFieldError("f-desc");
  }
  if (!payload.target_audience) {
    errors.push("Target Audience is required.");
    markFieldError("f-audience");
  }
  if (!payload.key_benefits.length) {
    errors.push("Add at least one Key Benefit.");
    markFieldError("f-benefits");
  }
  return errors;
}

async function parseErrorResponse(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    return JSON.stringify(data);
  } catch {
    try {
      return await response.text();
    } catch {
      return `Request failed with status ${response.status}`;
    }
  }
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
  sampleHint.style.color = bad ? "#a9342a" : "#4f5f72";
}

function toPublicAssetUrl(rawPath) {
  if (!rawPath) return "";
  if (/^data:|^https?:\/\//i.test(rawPath)) return rawPath;

  const normalized = String(rawPath).replaceAll("\\", "/");
  const lower = normalized.toLowerCase();
  let relative = normalized;
  const outputMarker = "/output/";
  const outputIndex = lower.lastIndexOf(outputMarker);

  if (outputIndex >= 0) {
    relative = normalized.slice(outputIndex + outputMarker.length);
  } else if (lower.startsWith("output/")) {
    relative = normalized.slice("output/".length);
  } else {
    const parts = normalized.split("/");
    const outputPartIndex = parts.map((part) => part.toLowerCase()).lastIndexOf("output");
    if (outputPartIndex >= 0) {
      relative = parts.slice(outputPartIndex + 1).join("/");
    }
  }

  return `${API_BASE_URL}/output/${relative.replace(/^\/+/, "")}`;
}

function showDashboard() {
  heroCard.classList.remove("hidden");
  loadingPanel.classList.add("hidden");
  // Only hide results if we haven't generated anything yet
  if (!chatContext.campaign) {
    resultsPanel.classList.add("hidden");
  } else {
    resultsPanel.classList.remove("hidden");
  }
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
  empty(finalsOutput, "Rendered ad creatives will appear here after generation.");
  empty(previewsOutput, "Platform previews will appear here after generation.");
  empty(hooksOutput, "Hooks will appear here after generation.");
  empty(anglesOutput, "Angles will appear here after generation.");
  empty(copyOutput, "Ad copy will appear here after generation.");
  empty(conceptsOutput, "Generated concepts will appear here after generation.");
  empty(exportsOutput, "Export rows will appear here after generation.");
  Object.keys(countTargets).forEach((key) => setCount(key, 0));
}

function activateTab(tab) {
  document.querySelectorAll(".tab").forEach((n) => n.classList.toggle("active", n.dataset.tab === tab));
  ["finals", "previews", "hooks", "angles", "copy", "concepts", "exports"].forEach((name) => {
    byId(`tab-${name}`).classList.toggle("hidden", tab !== name);
  });
  document.querySelectorAll(".specialist").forEach((n) => n.classList.toggle("active", n.dataset.agentTab === tab));
  dashboardNav.classList.remove("active");
  resultsTitle.textContent = "Campaign Output";
}

function list(target, items, render) {
  if (!items || !items.length) {
    empty(target, "No items.");
    return;
  }
  target.innerHTML = items.map((item, index) => render(item, index)).join("");
}

function fileNameFromPath(rawPath, fallback) {
  if (!rawPath) return fallback;
  const normalized = String(rawPath).replaceAll("\\", "/");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || fallback;
}

async function downloadAsset(event, url, filename) {
  event.preventDefault();
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Download failed");
    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);
  } catch (e) {
    console.error("Download error:", e);
    window.open(url, "_blank");
  }
}
window.downloadAsset = downloadAsset;

function downloadButton(url, filename, label) {
  if (!url) return "";
  const escUrl = esc(url);
  const escFile = esc(filename);
  return `<button class="download-btn" onclick="downloadAsset(event, '${escUrl}', '${escFile}')">${esc(label)}</button>`;
}

function renderScoreNote(asset) {
  const rationale = asset.score?.rationale || "";
  if (!rationale) return "";
  if (/heuristic review used/i.test(rationale)) return "";
  return `<div class="mono">${esc(rationale)}</div>`;
}

function humanizeToken(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function renderAll(data) {
  showResults();
  activateTab("finals");

  const hooks = data.hooks || [];
  const angles = data.angles || [];
  const copies = [...(data.ad_copies || [])].sort((a, b) => (b.total_score ?? -1) - (a.total_score ?? -1));
  const concepts = data.visual_concepts || [];
  const assets = data.creative_assets || [];
  const exportRows = data.export_rows || [];
  const previews = assets.filter((asset) => asset.preview);
  const campaignDir = data.output_directory || "";
  const csvUrl = campaignDir ? toPublicAssetUrl(`${campaignDir}\\exports\\meta_ads_bulk_upload.csv`) : "";
  const renderedCount = assets.filter((asset) => asset.rendered_ad).length;

  setCount("finals", renderedCount);
  setCount("previews", previews.length);
  setCount("hooks", hooks.length);
  setCount("angles", angles.length);
  setCount("copy", copies.length);
  setCount("concepts", concepts.length);
  setCount("exports", exportRows.length);

  chatContext = { ...chatContext, campaign: { hooks, angles, copies, concepts, assets, exportRows } };
  setStatus(`Generated ${renderedCount} full ad${renderedCount === 1 ? "" : "s"} with previews and export assets.`);

  list(finalsOutput, assets, (asset) => {
    const renderedUrl = toPublicAssetUrl(asset.rendered_ad?.image_path);
    const previewUrl = toPublicAssetUrl(asset.preview?.image_path);
    return `
      <div class="card card-creative">
        <div class="creative-grid">
          <div>
            ${renderedUrl ? `<img src="${renderedUrl}" class="concept-img" alt="Rendered ad">` : '<div class="card-inline-empty">Rendered output unavailable.</div>'}
          </div>
          <div class="creative-meta">
            <div class="pill-row">
              <span class="metric-pill">Rank ${esc(asset.score?.rank ?? "-")}</span>
              <span class="metric-pill">Score ${esc(asset.score?.total_score ?? "-")}</span>
              <span class="metric-pill">${esc(asset.platform)}</span>
            </div>
            <h3>${esc(asset.headline || asset.hook_text)}</h3>
            <div class="ad-copy-block">
              <div class="ad-copy-label">Primary Text</div>
              <p class="ad-copy-body">${esc(asset.primary_text || "Primary text unavailable.")}</p>
            </div>
            <div class="ad-copy-block">
              <div class="ad-copy-label">Headline</div>
              <p class="ad-copy-inline">${esc(asset.headline || asset.hook_text || "-")}</p>
            </div>
            <div class="ad-copy-inline-row">
              <div><strong>Description:</strong> ${esc(asset.description || "-")}</div>
              <div><strong>CTA:</strong> ${esc(asset.cta || "-")}</div>
            </div>
            <p><strong>Angle:</strong> ${esc(asset.angle_name)}</p>
            <p><strong>Hook Type:</strong> ${esc(humanizeToken(asset.hook_type || "-"))}</p>
            <p><strong>Image Provider:</strong> ${esc(asset.generated_creative?.provider || "-")} (${esc(asset.generated_creative?.status || "-")})</p>
            ${asset.generated_creative?.error ? `<div class="mono"><strong>Provider Error:</strong> ${esc(asset.generated_creative.error)}</div>` : ""}
            <p><strong>Concept:</strong> ${esc(asset.visual_concept?.scene_description || "-")}</p>
            <div class="download-row">
              ${downloadButton(renderedUrl, fileNameFromPath(asset.rendered_ad?.image_path, `${asset.concept_id}.png`), "Download PNG")}
              ${downloadButton(previewUrl, fileNameFromPath(asset.preview?.image_path, `${asset.concept_id}-preview.png`), "Download Preview")}
            </div>
            ${renderScoreNote(asset)}
          </div>
        </div>
      </div>
    `;
  });

  list(previewsOutput, previews, (asset) => {
    const previewUrl = toPublicAssetUrl(asset.preview?.image_path);
    return `
      <div class="card">
        <h3>${esc(asset.campaign_name)} | ${esc(asset.platform)} preview</h3>
        ${previewUrl ? `<img src="${previewUrl}" class="concept-img" alt="Feed preview">` : '<div class="card-inline-empty">Preview unavailable.</div>'}
        <p><strong>Primary Text:</strong> ${esc(asset.primary_text || "-")}</p>
        <p><strong>Headline:</strong> ${esc(asset.headline || "-")}</p>
        <div class="download-row">
          ${downloadButton(previewUrl, fileNameFromPath(asset.preview?.image_path, `${asset.concept_id}-preview.png`), "Download Preview")}
        </div>
      </div>
    `;
  });

  list(hooksOutput, hooks, (x) => `<div class="card"><h3>${esc(humanizeToken(x.type))}</h3><p>${esc(x.text)}</p><p>${esc(x.rationale)}</p></div>`);
  list(anglesOutput, angles, (x) => `<div class="card"><h3>${esc(x.name)}</h3><p>${esc(x.description)}</p><p>Emotion: ${esc(x.target_emotion)} | Use case: ${esc(x.use_case)}</p></div>`);
  list(copyOutput, copies, (x) => `<div class="card"><h3>${esc(x.headline)}</h3><p><strong>Primary Text:</strong> ${esc(x.primary_text)}</p><p><strong>Description:</strong> ${esc(x.description)}</p><p>CTA: ${esc(x.cta)} | Hook: ${esc(x.hook_text)}</p><div class="mono">Score: ${esc(x.total_score ?? "-")} | Rank: ${esc(x.score_rank ?? "-")} | Angle: ${esc(x.angle_name)}</div></div>`);
  list(conceptsOutput, concepts, (x) => `<div class="card"><h3>${esc(x.concept_id)} | ${esc(x.aspect_ratio)} | ${esc(x.media_type)}</h3><p>${esc(x.scene_description)}</p><div class="mono">${esc(x.generation_prompt)}</div></div>`);
  list(exportsOutput, exportRows, (row, index) => {
    const imageUrl = toPublicAssetUrl(row.image_path);
    const previewUrl = toPublicAssetUrl(row.preview_path);
    return `
    <div class="card">
      <h3>${esc(row.ad_name)}</h3>
      <p><strong>Campaign:</strong> ${esc(row.campaign_name)}</p>
      <p><strong>Ad Set:</strong> ${esc(row.ad_set_name)}</p>
      <p><strong>Headline:</strong> ${esc(row.headline)}</p>
      <p><strong>CTA:</strong> ${esc(row.cta)}</p>
      <div class="download-row">
        ${downloadButton(csvUrl, fileNameFromPath(csvUrl, "meta_ads_bulk_upload.csv"), index === 0 ? "Download CSV" : "CSV")}
        ${downloadButton(imageUrl, fileNameFromPath(row.image_path, `${row.ad_name}.png`), "Rendered PNG")}
        ${downloadButton(previewUrl, fileNameFromPath(row.preview_path, `${row.ad_name}-preview.png`), "Preview PNG")}
      </div>
      <div class="mono">${esc(row.image_path)}${row.preview_path ? `\n${esc(row.preview_path)}` : ""}</div>
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
    if (!res.ok) {
      throw new Error(await parseErrorResponse(res));
    }
    const data = await res.json();
    appendChat("ai", esc(data.reply || "No response received."));
    chatContext = data.context || chatContext;
    if (data.session_id && data.session_id !== chatSessionId) {
      chatSessionId = data.session_id;
      localStorage.setItem("chat_session_id", chatSessionId);
    }
  } catch (error) {
    appendChat("ai", esc(error.message || "Sorry, there was an error contacting the assistant."));
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
      chatBody.innerHTML = "";
      data.history.forEach((msg) => {
        appendChat(msg.role === "assistant" ? "ai" : "user", esc(msg.content));
      });
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

async function loadProviderHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/provider-health`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function buildPayload() {
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
    brand_colors: byId("f-brand-colors").value.split(",").map((s) => s.trim()).filter(Boolean),
    brand_fonts: byId("f-brand-fonts").value.split(",").map((s) => s.trim()).filter(Boolean),
    hook_count: parseInt(byId("f-hooks").value, 10) || 10,
    angle_count: parseInt(byId("f-angles").value, 10) || 3,
    copy_count: parseInt(byId("f-copy").value, 10) || 5,
    concept_count: parseInt(byId("f-concepts").value, 10) || 2,
    sample_images: []
  };

  if (logoInput && logoInput.files && logoInput.files[0]) {
    payload.logo_image = await getBase64(logoInput.files[0]);
  }

  const sampleFiles = sampleInput ? sampleInput.files : [];
  if (sampleFiles.length > 0) {
    setStatus("Processing upload images...");
    const selected = Array.from(sampleFiles).slice(0, MAX_SAMPLE_IMAGES);
    for (const file of selected) {
      if (!file.type.startsWith("image/") || file.size > MAX_SAMPLE_IMAGE_SIZE_BYTES) {
        continue;
      }
      try {
        payload.sample_images.push(await getBase64(file));
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

  return payload;
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
    setStatus("Finished ad workspace ready.");
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
        if (!res.ok) throw new Error(await parseErrorResponse(res));
        const data = await res.json();

        if (!data.items || data.items.length === 0) {
          empty(historyOutput, "No previous executions found.");
          return;
        }

        historyOutput.innerHTML = data.items.map((item) => {
          const primaryImage = toPublicAssetUrl(item.rendered_image_path || item.preview_image_path || (item.image_urls || [])[0]);
          const renderedUrl = toPublicAssetUrl(item.rendered_image_path);
          const previewUrl = toPublicAssetUrl(item.preview_image_path);
          return `
            <div class="card">
              <div class="history-head">
                <h3>${esc(item.campaign_name)}</h3>
                <span class="metric-pill">Score ${esc(item.total_score)}</span>
              </div>
              ${primaryImage ? `<img src="${primaryImage}" class="concept-img" alt="Creative image">` : ""}
              <p><strong>Headline:</strong> ${esc(item.headline || "-")}</p>
              <p><strong>CTA:</strong> ${esc(item.cta || "-")}</p>
              <div class="download-row">
                ${downloadButton(renderedUrl, fileNameFromPath(item.rendered_image_path, `${item.concept_id}.png`), "Rendered PNG")}
                ${downloadButton(previewUrl, fileNameFromPath(item.preview_image_path, `${item.concept_id}-preview.png`), "Preview PNG")}
              </div>
              <div class="mono">Platform: ${esc(item.platform)} | Concept: ${esc(item.concept_id)}</div>
            </div>
          `;
        }).join("");
      } catch (e) {
        empty(historyOutput, `Error loading execution history: ${esc(e.message || "Unknown error")}`);
      }
    });
  }

  heroGenerateButton.addEventListener("click", async () => {
    const payload = await buildPayload();
    const validationErrors = validatePayload(payload);
    if (validationErrors.length) {
      setStatus(validationErrors[0], true);
      byId("f-brand")?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    resetOutputs();
    showLoading();
    setStatus("Generating final ad package...");
    heroGenerateButton.disabled = true;
    heroGenerateButton.textContent = "Generating...";

    try {
      const response = await fetch(`${API_BASE_URL}/generate-creatives`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
      renderAll(data);
      const providerHealth = await loadProviderHealth();
      if (providerHealth) {
        const gr = providerHealth.groq;
        const g = providerHealth.gemini;
        const h = providerHealth.huggingface;
        const summary = `Providers: Groq ${gr?.ok ? "OK" : "Fail"} | Gemini ${g?.ok ? "OK" : "Fail"} | HF ${h?.ok ? "OK" : "Fail"}`;
        setStatus(summary, !(gr?.ok && h?.ok));
      }
    } catch (error) {
      setStatus(error.message || "Generation failed.", true);
      showDashboard();
    } finally {
      heroGenerateButton.disabled = false;
      heroGenerateButton.textContent = "Generate Final Ads";
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
      if (files.some((f) => f.size > MAX_SAMPLE_IMAGE_SIZE_BYTES)) {
        setSampleHint("One or more images are larger than 5MB and will be ignored.", true);
        return;
      }
      if (files.some((f) => !f.type.startsWith("image/"))) {
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
            const validSessions = data.sessions.filter((s) => s.session_id);
            if (validSessions.length > 0) {
              chatSessionsList.innerHTML = validSessions.map((s) => {
                const title = s.title ? s.title : "Session: " + String(s.session_id).substring(0, 8);
                return `<div class="chat-session-item" data-id="${s.session_id}" style="padding: 10px; border-bottom: 1px solid #e5e5e5; cursor: pointer; font-size: 0.9em;">
                  <strong>${esc(title)}</strong><br>
                  <span style="font-size: 0.8em; color: #666;">${new Date(s.last_activity).toLocaleString()}</span>
                </div>`;
              }).join("");

              document.querySelectorAll(".chat-session-item").forEach((item) => {
                item.addEventListener("click", () => {
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
        } catch {
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
