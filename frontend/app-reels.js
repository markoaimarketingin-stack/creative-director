
// ----------------------------------------------------------------------
// NEW REELS SCRIPT DIRECTOR LOGIC
// ----------------------------------------------------------------------

function switchReelsDirectorTab(tabName) {
  // Update Tab Buttons
  document.querySelectorAll(".reels-director-tabs .tab-btn").forEach(btn => {
    if (btn.dataset.reelsTab === tabName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Update Views
  const views = ["analyze", "trends", "generate"];
  views.forEach(v => {
    const el = document.getElementById("reels-tab-" + v);
    if (el) {
      if (v === tabName) {
        el.classList.remove("hidden");
      } else {
        el.classList.add("hidden");
      }
    }
  });

  // If opening trends tab for the first time, load defaults
  if (tabName === "trends") {
    generateDummyTrends();
  }
}

// 5MB Upload Limit Helper
function setupVideoUploadLimit(inputId, nameId) {
  const input = document.getElementById(inputId);
  const nameDisplay = document.getElementById(nameId);
  if (input) {
    input.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        if (file.size > 5 * 1024 * 1024) {
          nameDisplay.textContent = "Error: File exceeds 5MB limit. Please upload a smaller video.";
          nameDisplay.style.color = "#ef4444";
          input.value = ""; // Clear
        } else {
          nameDisplay.textContent = "Selected: " + file.name;
          nameDisplay.style.color = "#10b981"; // Green
        }
      } else {
        nameDisplay.textContent = "";
      }
    });
  }
}

// Setup limiters on DOM load (or immediately if appended at end)
setupVideoUploadLimit("reels-analyze-file", "reels-analyze-file-name");
setupVideoUploadLimit("reels-gen-ref-file", "reels-gen-ref-file-name");
function runReelsAnalyze() {
  const btn = document.getElementById("btn-reels-analyze");
  const urlInput = document.getElementById("reels-analyze-url");
  const fileInput = document.getElementById("reels-analyze-file");
  const subjectDisplay = document.getElementById("reels-analyze-subject");

  btn.textContent = "Analyzing...";
  btn.disabled = true;
  
  // Clear success messages
  const successMsg = document.getElementById("publishing-success-message");
  if (successMsg) successMsg.classList.add("hidden");
  
  // Clear output visibility during analysis
  document.getElementById("reels-analyze-output").classList.add("hidden");

  // Pause video player if playing
  const player = document.getElementById("mock-video-player");
  const bg = document.getElementById("mock-video-bg");
  if (player && bg) {
    player.pause();
    player.style.display = "none";
    bg.style.display = "flex";
  }
  
  // Simulate network delay
  setTimeout(() => {
    let subjectText = "Instagram Reel breakdown successfully generated.";
    const url = urlInput ? urlInput.value.trim() : "";
    const file = (fileInput && fileInput.files && fileInput.files[0]) ? fileInput.files[0].name : "";

    // Set mockup variables based on source
    let captionText = "";
    let publishDate = new Date().toLocaleDateString("en-US", { year: 'numeric', month: 'long', day: 'numeric' });
    let durationText = "15 seconds";
    let viewsNum = 0;
    let likesNum = 0;
    let commentsNum = 0;
    let sharesNum = 0;
    let engRate = 0;
    let avgWatch = 0;
    let retentionPath = "M0,0 Q15,40 50,60 T100,85 L100,100 L0,100 Z";
    let retentionStroke = "M0,0 Q15,40 50,60 T100,85";

    if (url) {
      subjectText = `Breakdown generated for URL: <a href="${url}" target="_blank" style="color: #ffffff; text-decoration: underline; font-weight: 600;">${url.substring(0, 45)}${url.length > 45 ? '...' : ''}</a>`;
      
      // Parse custom details based on URL keyword
      if (url.toLowerCase().includes("growth") || url.toLowerCase().includes("e1")) {
        captionText = "Struggling to grow on Instagram? Here is the exact daily process I use to gain 10k followers per month! 📈🚀 #growthmindset #instagramgrowth #socialmediatips";
        durationText = "15 seconds";
        viewsNum = 852400;
        likesNum = 64200;
        commentsNum = 1840;
        sharesNum = 12900;
        avgWatch = 11.8;
        // Good retention curve
        retentionPath = "M0,0 Q10,15 35,25 T100,45 L100,100 L0,100 Z";
        retentionStroke = "M0,0 Q10,15 35,25 T100,45";
      } else if (url.toLowerCase().includes("promo") || url.toLowerCase().includes("saas")) {
        captionText = "Meet Marko AI — the first AI-agent supervisor that auto-generates multi-channel ad packages in under 2 minutes. 🎥💻 #saas #aiart #marketingagency";
        durationText = "30 seconds";
        viewsNum = 145000;
        likesNum = 9200;
        commentsNum = 420;
        sharesNum = 1150;
        avgWatch = 18.5;
        // Moderate retention curve
        retentionPath = "M0,0 Q20,35 60,65 T100,80 L100,100 L0,100 Z";
        retentionStroke = "M0,0 Q20,35 60,65 T100,80";
      } else {
        captionText = "Stop writing boring copy! Use these 3 psychological triggers to double your conversions today. 🧠🔥 #copywriting #salesfunnel #marketing101";
        durationText = "20 seconds";
        viewsNum = 428000;
        likesNum = 31200;
        commentsNum = 980;
        sharesNum = 5400;
        avgWatch = 14.2;
        retentionPath = "M0,0 Q15,25 50,45 T100,65 L100,100 L0,100 Z";
        retentionStroke = "M0,0 Q15,25 50,45 T100,65";
      }
    } else if (file) {
      subjectText = `Breakdown generated for uploaded file: <strong style="color: #ffffff; font-weight: 600;">${file}</strong>`;
      captionText = `Quick tutorial on testing video hooks using the ${file} sample assets! 🎬🔥 #videotips #contentcreator #hooks`;
      durationText = "12 seconds";
      viewsNum = 52000;
      likesNum = 4100;
      commentsNum = 150;
      sharesNum = 620;
      avgWatch = 9.4;
      retentionPath = "M0,0 Q10,20 40,30 T100,50 L100,100 L0,100 Z";
      retentionStroke = "M0,0 Q10,20 40,30 T100,50";
    } else {
      subjectText = `Breakdown generated for demo reference reel.`;
      captionText = "Why copying competitors is keeping you broke (and what to do instead) 🤫💡 #socialmedia #businesshacks #entrepreneur";
      durationText = "15 seconds";
      viewsNum = 320000;
      likesNum = 24000;
      commentsNum = 740;
      sharesNum = 3800;
      avgWatch = 11.2;
      retentionPath = "M0,0 Q15,40 50,60 T100,85 L100,100 L0,100 Z";
      retentionStroke = "M0,0 Q15,40 50,60 T100,85";
    }

    // Calculate Engagement Rate
    engRate = ((likesNum + commentsNum + sharesNum) / viewsNum * 100).toFixed(2);

    // Update UI elements
    const capOverlay = document.getElementById("mockup-caption-overlay");
    const capDetail = document.getElementById("reels-detail-caption");
    const dateDetail = document.getElementById("reels-detail-date");
    const durDetail = document.getElementById("reels-detail-duration");
    const viewsEl = document.getElementById("anal-views");
    const likesEl = document.getElementById("anal-likes");
    const commsEl = document.getElementById("anal-comments");
    const sharesEl = document.getElementById("anal-shares");
    const engEl = document.getElementById("anal-engagement");
    const watchText = document.getElementById("average-watchtime-text");
    const rPath = document.getElementById("retention-path");
    const rStroke = document.getElementById("retention-stroke");
    const mockDur = document.getElementById("mock-video-duration");

    if (capOverlay) capOverlay.textContent = captionText;
    if (capDetail) capDetail.textContent = captionText;
    if (dateDetail) dateDetail.textContent = publishDate;
    if (durDetail) durDetail.textContent = durationText;
    if (mockDur) mockDur.textContent = `0:00 / 0:${durationText.split(" ")[0]}`;
    
    if (viewsEl) viewsEl.textContent = viewsNum >= 1000 ? (viewsNum / 1000).toFixed(1) + "K" : viewsNum;
    if (likesEl) likesEl.textContent = likesNum >= 1000 ? (likesNum / 1000).toFixed(1) + "K" : likesNum;
    if (commsEl) commsEl.textContent = commentsNum >= 1000 ? (commentsNum / 1000).toFixed(1) + "K" : commentsNum;
    if (sharesEl) sharesEl.textContent = sharesNum >= 1000 ? (sharesNum / 1000).toFixed(1) + "K" : sharesNum;
    if (engEl) engEl.textContent = engRate + "%";
    if (watchText) watchText.textContent = `Avg Watch Time: ${avgWatch}s`;
    
    if (rPath) rPath.setAttribute("d", retentionPath);
    if (rStroke) rStroke.setAttribute("d", retentionStroke);

    if (subjectDisplay) subjectDisplay.innerHTML = subjectText;

    document.getElementById("reels-analyze-output").classList.remove("hidden");
    btn.textContent = "Analyze Reel";
    btn.disabled = false;
  }, 1500);
}
function runReelsGenerate() {
  const btn = document.getElementById("btn-reels-generate");
  const ctx = document.getElementById("reels-gen-context").value || "Generic trending topic";
  const duration = document.getElementById("reels-gen-duration").value;
  
  btn.textContent = "Generating...";
  btn.disabled = true;
  
  // Simulate network delay
  setTimeout(() => {
    document.getElementById("reels-generate-output").classList.remove("hidden");
    document.getElementById("reels-out-title").textContent = "Generated Script (" + duration + ")";
    document.getElementById("reels-out-script").textContent = 
      "Title: 3 SECRETS to Mastering " + ctx + "\n\n" +
      "[0:00 - 0:03] HOOK: Visual: Fast zoom in on face. Audio: 'Stop scrolling! You are doing " + ctx + " completely wrong.'\n\n" +
      "[0:03 - 0:10] BODY 1: Visual: B-Roll showing frustration. Audio: 'Most people think the secret is grinding harder, but actually...'\n\n" +
      "[0:10 - 0:20] BODY 2: Visual: Screen recording or chart. Audio: '...the real secret is leveraging this exact system I\\'ve been using for 5 years.'\n\n" +
      "[0:20 - 0:25] CTA: Visual: Pointing to comments. Audio: 'Comment \"SYSTEM\" below and I will DM you the exact blueprint.'\n\n" +
      "Hashtags: #viral #growth #strategy";
    
    btn.textContent = "Generate Script";
    btn.disabled = false;
  }, 2000);
}

function generateDummyTrends() {
  const category = document.getElementById("reels-trends-category").value;
  const grid = document.getElementById("reels-trends-grid");
  const hash = document.getElementById("reels-trends-hashtags");
  const audio = document.getElementById("reels-trends-audio");
  
  if (!grid) return;
  
  // Mock Data
  const thumbnails = [
    "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=300&q=80",
    "https://images.unsplash.com/photo-1516259762381-22954d7d3ad2?w=300&q=80",
    "https://images.unsplash.com/photo-1542204165-65bf26472b9b?w=300&q=80",
    "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300&q=80",
    "https://images.unsplash.com/photo-1533227260828-53134ce46eba?w=300&q=80"
  ];
  
  let html = "";
  for(let i=0; i<5; i++) {
    const views = Math.floor(Math.random() * 500) + 10;
    const likes = Math.floor(views * 0.1);
    const shares = Math.floor(views * 0.05);
    html += `
      <div class="card" style="display: flex; gap: 12px; padding: 12px; background: #111114; align-items: center; cursor: pointer;">
        <img src="${thumbnails[i]}" style="width: 60px; height: 100px; object-fit: cover; border-radius: 6px; flex-shrink: 0;" alt="Reel">
        <div>
          <h4 style="margin: 0 0 4px 0; color: #fff;">Viral Pattern #${i+1}</h4>
          <p style="margin: 0 0 8px 0; font-size: 0.85rem; color: #a1a1aa;">Excellent retention in first 3s.</p>
          <div style="display: flex; gap: 12px; font-size: 0.8rem; color: #71717a;">
            <span>👁 ${views}K</span>
            <span>❤ ${likes}K</span>
            <span>↗ ${shares}K</span>
          </div>
        </div>
      </div>
    `;
  }
  grid.innerHTML = html;
  
  hash.innerHTML = `
    <span class="top-pill">#${category}</span>
    <span class="top-pill">#${category}tips</span>
    <span class="top-pill">#viral</span>
    <span class="top-pill">#trending</span>
    <span class="top-pill">#growth</span>
  `;
  
  audio.innerHTML = `
    1. "${category.toUpperCase()} Motivation Type Beat" - 2.5M Uses ⬆<br><br>
    2. "Trending Voiceover #42" - 1.1M Uses ⬆<br><br>
    3. "Chill Vibes 2024" - 800K Uses ➖
  `;
}

// Reels Script Director Helper Functions
function fillSampleReelUrl(url) {
  const urlInput = document.getElementById("reels-analyze-url");
  if (urlInput) {
    urlInput.value = url;
  }
}

function toggleMockVideoPlay() {
  const player = document.getElementById("mock-video-player");
  const bg = document.getElementById("mock-video-bg");
  if (!player || !bg) return;
  if (player.paused) {
    player.style.display = "block";
    bg.style.display = "none";
    player.play();
  } else {
    player.pause();
    player.style.display = "none";
    bg.style.display = "flex";
  }
}

function downloadMockReelVideo() {
  const link = document.createElement("a");
  link.href = "https://assets.mixkit.co/videos/preview/mixkit-holding-a-smartphone-showing-a-social-network-app-41586-large.mp4";
  link.download = "marko_ai_instagram_reel.mp4";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToastNotification("Downloading Reel video file...");
}

function openPostReelModal() {
  const modal = document.getElementById("post-reel-modal");
  const captionInput = document.getElementById("post-reel-caption");
  const currentCaption = document.getElementById("reels-detail-caption");
  
  if (captionInput && currentCaption) {
    captionInput.value = currentCaption.textContent;
  }
  if (modal) {
    modal.classList.remove("hidden");
  }
}

function closePostReelModal() {
  const modal = document.getElementById("post-reel-modal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

function togglePostReelSchedule(show) {
  const wrap = document.getElementById("post-reel-schedule-time-wrap");
  const btn = document.getElementById("btn-confirm-post-reel");
  if (wrap) {
    if (show) {
      wrap.classList.remove("hidden");
      if (btn) btn.textContent = "Schedule Post";
    } else {
      wrap.classList.add("hidden");
      if (btn) btn.textContent = "Publish Now";
    }
  }
}

function executePostReel() {
  const btn = document.getElementById("btn-confirm-post-reel");
  const account = document.getElementById("post-reel-account").value;
  const scheduleType = document.querySelector('input[name="post-reel-schedule-type"]:checked').value;
  const time = document.getElementById("post-reel-schedule-time").value;
  
  if (btn) {
    btn.textContent = scheduleType === "later" ? "Scheduling..." : "Publishing...";
    btn.disabled = true;
  }
  
  setTimeout(() => {
    if (btn) {
      btn.disabled = false;
      btn.textContent = scheduleType === "later" ? "Schedule Post" : "Publish Now";
    }
    closePostReelModal();
    
    const successMsg = document.getElementById("publishing-success-message");
    const successDetails = document.getElementById("publishing-success-details");
    
    if (successMsg && successDetails) {
      successMsg.classList.remove("hidden");
      if (scheduleType === "later") {
        const formattedTime = time ? new Date(time).toLocaleString() : "scheduled date";
        successDetails.textContent = `Reel scheduled successfully for ${formattedTime} to @${account}.`;
      } else {
        successDetails.textContent = `Reel successfully posted to @${account}.`;
      }
    }
    showToastNotification("Reel published successfully!");
  }, 1800);
}

// Expose to window
window.fillSampleReelUrl = fillSampleReelUrl;
window.toggleMockVideoPlay = toggleMockVideoPlay;
window.downloadMockReelVideo = downloadMockReelVideo;
window.openPostReelModal = openPostReelModal;
window.closePostReelModal = closePostReelModal;
window.togglePostReelSchedule = togglePostReelSchedule;
window.executePostReel = executePostReel;
