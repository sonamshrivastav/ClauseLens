// ClauseLens AI — Factual Document Intelligence Client Logic (Bug-Free Version)

let activeDocId = null;
let currentDocData = null;

// Safe DOM Helper Functions
function escapeHTML(str) {
  if (str === null || str === undefined) return "";
  return String(str).replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

function safeSetText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function safeSetHTML(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function safeSetDisplay(id, displayStyle) {
  const el = document.getElementById(id);
  if (el) el.style.display = displayStyle;
}

document.addEventListener("DOMContentLoaded", () => {
  initUploadHandler();
  initTabNavigation();
  initChatSystem();
});

// File & Text Upload Handler
function initUploadHandler() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const pasteInput = document.getElementById("pasteInput");
  const btnAnalyzePasted = document.getElementById("btnAnalyzePasted");

  if (!dropZone || !fileInput) return;

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
  });

  // Accessibility: Keyboard support for dropZone
  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
    e.target.value = "";
  });

  if (btnAnalyzePasted) {
    btnAnalyzePasted.addEventListener("click", () => {
      const text = pasteInput ? pasteInput.value.trim() : "";
      if (!text) {
        alert("Please paste contract text to analyze.");
        return;
      }
      handleTextAnalysis(text);
    });
  }
}

async function handleFileUpload(file) {
  clearPreviousAnalysis();
  showLoading(true);
  const formData = new FormData();
  formData.append("file", file);
  
  const providerEl = document.getElementById("providerSelect");
  const provider = providerEl ? providerEl.value : "auto";
  formData.append("provider", provider);

  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Upload failed");
    }

    const data = await response.json();
    activeDocId = data.doc_id;
    currentDocData = data;
    renderAnalysisView(data);
    showLoading(false);
  } catch (err) {
    showLoading(false);
    setTimeout(() => alert(`Error analyzing document: ${err.message}`), 10);
  }
}

async function handleTextAnalysis(text) {
  clearPreviousAnalysis();
  showLoading(true);
  const providerEl = document.getElementById("providerSelect");
  const provider = providerEl ? providerEl.value : "auto";

  try {
    const response = await fetch("/api/analyze-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, provider })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Analysis failed");
    }

    const data = await response.json();
    activeDocId = data.doc_id;
    currentDocData = data;
    renderAnalysisView(data);
    showLoading(false);
  } catch (err) {
    showLoading(false);
    setTimeout(() => alert(`Error: ${err.message}`), 10);
  }
}

function renderAnalysisView(data) {
  if (!data) return;
  const analysis = data.analysis || {};
  const findings = analysis.findings || [];

  safeSetText("docTitleDisplay", data.title || "Uploaded Contract");
  safeSetText("docSummaryDisplay", analysis.summary || "Factual legal clause breakdown & blind spot analysis.");
  safeSetText("docTypeBadge", analysis.document_type || "Contract");

  // Calculate factual counts
  let countImportant = findings.filter(f => f.category === "important_review" || f.severity === "important").length;
  let countAmbiguities = findings.filter(f => f.category === "ambiguity").length;
  let countBlindSpots = findings.filter(f => f.category === "blind_spot").length;
  if (analysis.blind_spots && analysis.blind_spots.length > countBlindSpots) {
    countBlindSpots = analysis.blind_spots.length;
  }
  let countObligations = findings.filter(f => f.category === "obligation").length;

  safeSetText("countImportant", countImportant);
  safeSetText("countAmbiguities", countAmbiguities);
  safeSetText("countBlindSpots", countBlindSpots);
  safeSetText("countObligations", countObligations);

  // Render Blind Spots Section
  const blindSpotsArray = analysis.blind_spots || [];
  if (blindSpotsArray.length > 0) {
    safeSetDisplay("blindSpotsContainer", "block");
    safeSetHTML("blindSpotsList", blindSpotsArray.map(bs => `<li><span>⚠️</span> <div>${escapeHTML(bs)}</div></li>`).join(""));
  } else {
    const bsFromFindings = findings.filter(f => f.category === "blind_spot" || f.what_is_unclear).map(f => f.what_is_unclear || f.why_it_matters);
    if (bsFromFindings.length > 0) {
      safeSetDisplay("blindSpotsContainer", "block");
      safeSetHTML("blindSpotsList", bsFromFindings.map(bs => `<li><span>⚠️</span> <div>${escapeHTML(bs)}</div></li>`).join(""));
    } else {
      safeSetDisplay("blindSpotsContainer", "none");
    }
  }

  // Render Key Obligations Summary List
  const obligationsArray = analysis.key_obligations || [];
  if (obligationsArray.length > 0) {
    safeSetHTML("keyObligationsList", obligationsArray.map(ob => `<li>${escapeHTML(ob)}</li>`).join(""));
  } else {
    safeSetHTML("keyObligationsList", `<li style="color:var(--text-muted);">Standard document obligations apply.</li>`);
  }

  // Render Important Dates Summary List
  const datesArray = analysis.important_dates || [];
  if (datesArray.length > 0) {
    safeSetHTML("importantDatesList", datesArray.map(d => `<li>${escapeHTML(d)}</li>`).join(""));
  } else {
    safeSetHTML("importantDatesList", `<li style="color:var(--text-muted);">No specific deadlines identified.</li>`);
  }

  // Render Detailed Structured Findings
  const container = document.getElementById("clauseListContainer");
  if (container) {
    container.innerHTML = "";

    findings.forEach(finding => {
      const card = document.createElement("div");
      card.className = "clause-card";

      let catBadgeClass = "badge-clear";
      let catBadgeLabel = "🟢 CLEAR";
      if (finding.category === "important_review") {
        catBadgeClass = "badge-important";
        catBadgeLabel = "🔴 IMPORTANT TO REVIEW";
      } else if (finding.category === "ambiguity") {
        catBadgeClass = "badge-ambiguity";
        catBadgeLabel = "🟡 UNCLEAR / AMBIGUOUS";
      } else if (finding.category === "blind_spot") {
        catBadgeClass = "badge-blindspot";
        catBadgeLabel = "👀 POTENTIAL BLIND SPOT";
      } else if (finding.category === "obligation") {
        catBadgeClass = "badge-obligation";
        catBadgeLabel = "📌 KEY OBLIGATION";
      }

      const whatSays = escapeHTML(finding.what_document_says || finding.source_text || "");
      const plain = escapeHTML(finding.plain_language || "");
      const matters = escapeHTML(finding.why_it_matters || "");
      const unclear = escapeHTML(finding.what_is_unclear || "");
      const question = escapeHTML(finding.question_to_clarify || "");
      const sourceSec = escapeHTML(finding.source_section || "Section");
      const titleEsc = escapeHTML(finding.title || 'Clause');
      const sourcePage = escapeHTML(finding.source_page || "");

      let unclearHtml = "";
      if (unclear && unclear.trim()) {
        unclearHtml = `
          <div class="finding-section">
            <div class="finding-label label-unclear"><span>🟡</span> What Is Unclear / Missing</div>
            <div class="box-unclear">${unclear}</div>
          </div>
        `;
      }

      let questionHtml = "";
      if (question && question.trim()) {
        questionHtml = `
          <div class="finding-section">
            <div class="finding-label label-question"><span>❓</span> Question To Clarify</div>
            <div class="box-question">${question}</div>
          </div>
        `;
      }

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1rem;">
          <div>
            <span style="font-family:var(--font-mono); font-size:0.8rem; color:var(--text-secondary);">${sourceSec}</span>
            <h3 style="font-size:1.15rem; font-weight:800; margin-top:0.2rem;">${titleEsc}</h3>
          </div>
          <span class="category-badge ${catBadgeClass}">${catBadgeLabel}</span>
        </div>

        <div class="finding-section">
          <div class="finding-label label-says"><span>📜</span> What The Document Says</div>
          <div class="box-says">"${whatSays}"</div>
        </div>

        <div class="finding-section">
          <div class="finding-label label-plain"><span>💡</span> What It Means In Plain Language</div>
          <div class="box-plain">${plain}</div>
        </div>

        <div class="finding-section">
          <div class="finding-label label-matters"><span>⚠️</span> Why You May Want To Pay Attention</div>
          <div class="box-matters">${matters}</div>
        </div>

        ${unclearHtml}
        ${questionHtml}

        <div class="source-tag">
          Source: ${sourceSec} ${sourcePage ? '• Page ' + sourcePage : ''}
        </div>
      `;

      container.appendChild(card);
    });
  }

  // Render Suggested Clarifications
  renderSuggestedClarifications(findings, data.title);
}

function renderSuggestedClarifications(findings, title) {
  const container = document.getElementById("negotiationScriptContainer");
  if (!container) return;

  const unclearOrQuestions = findings.filter(f => f.question_to_clarify || f.what_is_unclear || f.category === "ambiguity" || f.category === "blind_spot");

  const bulletQuestions = unclearOrQuestions.map(f => {
    const q = f.question_to_clarify || f.what_is_unclear;
    return `• ${f.source_section} (${f.title}): ${q}`;
  }).join("\n\n");

  const emailText = `Subject: Clarification Questions — ${title}

Dear Signing Team,

Thank you for sending over the agreement. I am reviewing the terms and would appreciate a brief clarification on the following points:

${bulletQuestions || "• Requesting confirmation on specific notice periods and deposit return timelines."}

Could you please confirm or clarify these specific items? I appreciate your assistance!

Best regards,
[Your Name]`;

  container.innerHTML = `
    <div style="background:var(--bg-card); border:1px solid var(--bg-card-border); border-radius:var(--radius-lg); padding:1.5rem;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
        <div>
          <h3 style="font-size:1.1rem; font-weight:800;">Suggested Clarifications</h3>
          <p style="font-size:0.8rem; color:var(--text-secondary);">Neutral clarification request template based on unstated or ambiguous document clauses.</p>
        </div>
        <button class="btn-primary" onclick="navigator.clipboard.writeText(document.getElementById('scriptArea').innerText); alert('Copied to clipboard!');">📋 Copy Questions</button>
      </div>

      <div style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); color:#fde68a; font-size:0.8rem; padding:0.5rem 0.85rem; border-radius:6px; margin-bottom:1rem;">
        ⚠️ <strong>Note:</strong> Suggested clarification — review with a qualified professional before using.
      </div>

      <pre id="scriptArea" style="background:rgba(0,0,0,0.5); padding:1.25rem; border-radius:8px; font-family:var(--font-mono); font-size:0.875rem; color:#e0e7ff; white-space:pre-wrap; line-height:1.6;">${emailText}</pre>
    </div>
  `;
}

// Grounded AI Chat System
function initChatSystem() {
  const chatInput = document.getElementById("chatInput");
  const btnSend = document.getElementById("btnSendChat");

  if (!chatInput || !btnSend) return;

  async function handleChat() {
    const text = chatInput.value.trim();
    if (!text) return;

    if (!activeDocId) {
      alert("Please upload or paste a contract first before asking questions!");
      return;
    }

    appendMsg(text, "user");
    chatInput.value = "";
    
    // Add loading bubble
    const loadingId = "loading-" + Date.now();
    const container = document.getElementById("chatMessages");
    if (container) {
      const bubble = document.createElement("div");
      bubble.id = loadingId;
      bubble.className = "msg-bubble msg-ai";
      bubble.innerHTML = `<div><span style="font-style:italic; color:#888;">ClauseLens AI is thinking...</span></div>`;
      container.appendChild(bubble);
      container.scrollTop = container.scrollHeight;
    }

    const providerEl = document.getElementById("providerSelect");
    const provider = providerEl ? providerEl.value : "auto";

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id: activeDocId, question: text, provider })
      });

      if (!response.ok) throw new Error("Chat request failed");
      const data = await response.json();
      
      const loadingEl = document.getElementById(loadingId);
      if (loadingEl) loadingEl.remove();
      
      appendMsg(data.answer, "ai", data.citation);
    } catch (err) {
      const loadingEl = document.getElementById(loadingId);
      if (loadingEl) loadingEl.remove();
      appendMsg("I could not process your query against the document context.", "ai");
    }
  }

  btnSend.addEventListener("click", handleChat);
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleChat();
  });
}

function appendMsg(text, sender, citation = null) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = `msg-bubble ${sender === 'user' ? 'msg-user' : 'msg-ai'}`;

  let html = `<div>${escapeHTML(text)}</div>`;
  if (citation) {
    html += `<div style="font-size:0.75rem; color:#a5b4fc; margin-top:0.4rem; font-weight:700;">📌 Citation: ${escapeHTML(citation)}</div>`;
  }
  bubble.innerHTML = html;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}


// Tab Switching
function initTabNavigation() {
  const tabs = document.querySelectorAll(".tab-btn");
  const contents = document.querySelectorAll(".tab-content");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      contents.forEach(c => c.classList.remove("active"));

      tab.classList.add("active");
      const target = tab.getAttribute("data-tab");
      const targetEl = document.getElementById(target);
      if (targetEl) targetEl.classList.add("active");
    });
  });
}

function showLoading(show) {
  safeSetDisplay("loadingIndicator", show ? "block" : "none");
}

function clearPreviousAnalysis() {
  activeDocId = null;
  currentDocData = null;
  
  safeSetText("docTitleDisplay", "Upload a document above to begin analysis");
  safeSetText("docSummaryDisplay", "Factual clause analysis and blind spot identification.");
  safeSetText("docTypeBadge", "Contract");
  
  safeSetText("countImportant", "0");
  safeSetText("countAmbiguities", "0");
  safeSetText("countBlindSpots", "0");
  safeSetText("countObligations", "0");
  
  safeSetDisplay("blindSpotsContainer", "none");
  safeSetHTML("blindSpotsList", "");
  safeSetHTML("keyObligationsList", "");
  safeSetHTML("importantDatesList", "");
  
  const container = document.getElementById("clauseListContainer");
  if (container) {
    container.innerHTML = `<div style="text-align:center; padding:3rem; color:var(--text-secondary);">Upload a document or paste text above to view clause breakdown.</div>`;
  }
  
  const negContainer = document.getElementById("negotiationScriptContainer");
  if (negContainer) {
    negContainer.innerHTML = "";
  }
  
  const chatMessages = document.getElementById("chatMessages");
  if (chatMessages) {
    chatMessages.innerHTML = `<div class="msg-bubble msg-ai"><div>Please upload a document to begin chatting.</div></div>`;
  }
}
