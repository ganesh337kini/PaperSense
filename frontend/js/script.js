const API_BASE = "";

// State management
let selectedPapers = new Set();
let currentPaperId = null;
let currentReportContent = null;
let allUploadedPapers = [];

// =============================================
// Universal Toast Notification System
// =============================================
function showToast(message, type = "info", duration = 4000) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const icons = {
    info: "ℹ️",
    success: "✅",
    warning: "⚠️",
    error: "❌"
  };

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || "ℹ️"}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button class="toast-close" title="Dismiss">&times;</button>
  `;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  const dismiss = () => {
    toast.classList.remove("show");
    toast.classList.add("hide");
    setTimeout(() => {
      if (toast.parentElement) toast.parentElement.removeChild(toast);
    }, 300);
  };

  toast.querySelector(".toast-close").addEventListener("click", dismiss);

  if (duration > 0) {
    setTimeout(dismiss, duration);
  }
}

// Navigation
function setupNavigation() {
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const page = link.dataset.page;
      navigateTo(page);
    });
  });
}

function navigateTo(page) {
  // Update nav links
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.remove('active');
    if (link.dataset.page === page) {
      link.classList.add('active');
    }
  });

  // Update pages
  document.querySelectorAll('.page').forEach(p => {
    p.classList.remove('active');
  });
  document.getElementById(`page-${page}`).classList.add('active');

  // Load page-specific data
  if (page === 'papers') {
    loadPapers();
  } else if (page === 'reports') {
    loadReports();
  } else if (page === 'chat') {
    setupChatPage();
  } else if (page === 'peer-review') {
    setupPeerReviewPage();
  } else if (page === 'citations') {
    setupCitationsPage();
  } else if (page === 'hypothesis') {
    setupHypothesisPage();
  }
}

// Backend health check
async function checkBackendHealth() {
  const statusEl = document.getElementById("backend-status");
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();
    statusEl.textContent = `online (${data.app} v${data.version})`;
    statusEl.className = "ok";
  } catch (err) {
    statusEl.textContent = "unreachable — is uvicorn running?";
    statusEl.className = "down";
  }
}

// Search functionality
async function handleSearchSubmit(event) {
  event.preventDefault();

  const input = document.getElementById("query-input");
  const statusLine = document.getElementById("status-line");
  const resultsEl = document.getElementById("results");
  const searchBtn = document.getElementById("search-btn");
  const openAccessFilter = document.getElementById("open-access-filter").checked;
  const sortBy = document.getElementById("sort-select").value;
  const query = input.value.trim();

  if (!query) return;

  statusLine.textContent = "Searching academic papers...";
  resultsEl.innerHTML = "";
  searchBtn.disabled = true;
  showToast(`🔍 Searching papers for "${query}"...`, "info", 2500);

  try {
    let url = `${API_BASE}/api/search?query=${encodeURIComponent(query)}&sort_by=${sortBy}`;
    if (openAccessFilter) {
      url += "&open_access_only=true";
    }

    const response = await fetch(url);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || `Search failed (${response.status})`);
    }

    statusLine.textContent = `Found ${data.total_results} papers for "${query}".`;
    showToast(`✅ Found ${data.total_results} papers.`, "success");

    if (!data.papers || data.papers.length === 0) {
      resultsEl.innerHTML = "<p>No research papers found.</p>";
      return;
    }

    data.papers.forEach((paper, index) => {
      const card = document.createElement("article");
      card.className = "paper-card";

      const title = document.createElement("h3");
      title.textContent = `${index + 1}. ${paper.title || "Untitled"}`;
      card.appendChild(title);

      const meta = document.createElement("p");
      meta.className = "meta";
      const authorText = paper.authors?.length
        ? paper.authors.slice(0, 5).join(", ") + (paper.authors.length > 5 ? " et al." : "")
        : "Authors unavailable";
      const sourceText = paper.source ? ` • ${paper.source}` : "";
      const oaBadge = paper.is_open_access ? " 🟢 Open Access" : "";
      meta.textContent = `${authorText} • ${paper.year || "Year unavailable"}${sourceText}${oaBadge}`;
      card.appendChild(meta);

      if (paper.abstract) {
        const abstract = document.createElement("p");
        abstract.className = "meta";
        abstract.textContent = paper.abstract.substring(0, 300) + (paper.abstract.length > 300 ? "..." : "");
        card.appendChild(abstract);
      }

      const citations = document.createElement("p");
      citations.textContent = `Citations: ${paper.citations ?? 0}`;
      card.appendChild(citations);

      const targetUrl = paper.url || paper.doi || paper.openalex_url;
      if (targetUrl) {
        const link = document.createElement("a");
        link.href = targetUrl;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "View paper";
        card.appendChild(link);
      }

      resultsEl.appendChild(card);
    });
  } catch (error) {
    console.error(error);
    statusLine.textContent = "Search failed.";
    showToast(`❌ Search failed: ${error.message}`, "error");
    const message = document.createElement("p");
    message.textContent = error.message || "Unable to retrieve research papers.";
    resultsEl.replaceChildren(message);
  } finally {
    searchBtn.disabled = false;
  }
}

// Upload functionality
async function handleUploadSubmit(event) {
  event.preventDefault();

  const fileInput = document.getElementById("pdf-file");
  const statusLine = document.getElementById("upload-status");
  const uploadBtn = document.getElementById("upload-btn");
  const resultsEl = document.getElementById("upload-results");

  const file = fileInput.files[0];
  if (!file) {
    statusLine.textContent = "Please select a PDF file.";
    showToast("⚠️ Please select a PDF file first.", "warning");
    return;
  }

  statusLine.textContent = "Uploading and processing PDF...";
  showToast(`📤 Uploading "${file.name}" & extracting chunks...`, "info", 5000);
  resultsEl.innerHTML = "";
  uploadBtn.disabled = true;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || `Upload failed (${response.status})`);
    }

    statusLine.textContent = `Upload successful: ${data.chunks_created} chunks extracted.`;
    showToast(`✅ Paper "${data.title}" indexed (${data.chunks_created} chunks)!`, "success", 5000);

    const card = document.createElement("article");
    card.className = "paper-card";
    card.innerHTML = `
      <h3>${data.title}</h3>
      <p class="meta">Pages: ${data.total_pages} | Chunks: ${data.chunks_created}</p>
      <p class="meta">Status: Completed</p>
    `;
    resultsEl.appendChild(card);

    fileInput.value = "";
  } catch (error) {
    console.error(error);
    statusLine.textContent = "Upload failed.";
    showToast(`❌ Upload failed: ${error.message}`, "error", 5000);
    const message = document.createElement("p");
    message.textContent = error.message || "Unable to upload PDF.";
    resultsEl.replaceChildren(message);
  } finally {
    uploadBtn.disabled = false;
  }
}

// Load papers
async function loadPapers() {
  const papersList = document.getElementById("papers-list");
  papersList.innerHTML = "<p>Loading papers...</p>";

  try {
    const response = await fetch(`${API_BASE}/api/papers`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to load papers");
    }

    allUploadedPapers = data.papers || [];
    populateChatPaperSelect();

    papersList.innerHTML = "";

    if (!data.papers || data.papers.length === 0) {
      papersList.innerHTML = "<p>No papers uploaded yet.</p>";
      return;
    }

    data.papers.forEach(paper => {
      const item = document.createElement("div");
      item.className = "paper-item";
      
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.dataset.paperId = paper.id;
      checkbox.addEventListener("change", handlePaperSelection);
      
      const info = document.createElement("div");
      info.className = "paper-item-info";
      
      const title = document.createElement("h3");
      title.textContent = paper.title;
      
      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `Uploaded: ${new Date(paper.created_at).toLocaleDateString()}`;
      
      const statusBadge = document.createElement("span");
      statusBadge.className = `status-badge ${paper.processing_status}`;
      statusBadge.textContent = paper.processing_status;

      info.appendChild(title);
      info.appendChild(meta);
      info.appendChild(statusBadge);
      
      item.appendChild(checkbox);
      item.appendChild(info);
      
      // Add click handler for viewing details
      info.addEventListener("click", () => showPaperDetails(paper.id));
      
      papersList.appendChild(item);
    });
  } catch (error) {
    console.error(error);
    papersList.innerHTML = "<p>Failed to load papers.</p>";
  }
}

function handlePaperSelection(event) {
  const paperId = parseInt(event.target.dataset.paperId);
  if (event.target.checked) {
    selectedPapers.add(paperId);
  } else {
    selectedPapers.delete(paperId);
  }
  
  updateToolbarButtons();
}

function updateToolbarButtons() {
  const compareBtn = document.getElementById("compare-selected-btn");
  const gapsBtn = document.getElementById("detect-gaps-btn");
  const reportBtn = document.getElementById("generate-report-btn");
  const statusEl = document.getElementById("papers-toolbar-status");

  const count = selectedPapers.size;

  // Keep buttons interactive so clicking them provides friendly guidance
  compareBtn.removeAttribute("disabled");
  gapsBtn.removeAttribute("disabled");
  reportBtn.removeAttribute("disabled");

  compareBtn.style.opacity = count < 2 ? "0.75" : "1";
  gapsBtn.style.opacity = count < 2 ? "0.75" : "1";
  reportBtn.style.opacity = count < 1 ? "0.75" : "1";

  if (count === 0) {
    statusEl.textContent = "☑️ Check papers below to compare findings, detect gaps, or generate reports.";
    statusEl.className = "toolbar-status hint";
  } else if (count === 1) {
    statusEl.textContent = `✅ 1 paper selected — select 1 more to compare or detect research gaps.`;
    statusEl.className = "toolbar-status hint";
  } else {
    statusEl.textContent = `✅ ${count} papers selected — all comparison tools ready.`;
    statusEl.className = "toolbar-status success";
  }
}

async function showPaperDetails(paperId) {
  currentPaperId = paperId;
  
  try {
    const response = await fetch(`${API_BASE}/api/papers/${paperId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to load paper");
    }

    const paper = data.paper;
    document.getElementById("modal-title").textContent = paper.title;
    
    let body = `
      <p><strong>Authors:</strong> ${paper.authors || "N/A"}</p>
      <p><strong>Year:</strong> ${paper.year || "N/A"}</p>
      <p><strong>Pages:</strong> ${paper.total_pages || "N/A"}</p>
      <p><strong>Status:</strong> ${paper.processing_status}</p>
      <p><strong>Chunks:</strong> ${data.chunks.length}</p>
    `;
    
    if (paper.processing_error) {
      body += `<p style="color: #ef4444;"><strong>Error:</strong> ${paper.processing_error}</p>`;
    }
    
    document.getElementById("modal-body").innerHTML = body;
    document.getElementById("paper-modal").style.display = "block";
    
  } catch (error) {
    console.error(error);
    showToast("❌ Failed to load paper details: " + error.message, "error");
  }
}

async function analyzePaper() {
  if (!currentPaperId) return;
  
  const analyzeBtn = document.getElementById("analyze-paper-btn");
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing...";
  showToast("🧠 Running AI analysis on paper...", "info", 3000);
  
  try {
    const response = await fetch(`${API_BASE}/api/analyze/${currentPaperId}`, {
      method: "POST"
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Analysis failed");
    }

    displayAnalysis(data.analysis);
    document.getElementById("paper-modal").style.display = "none";
    showToast("✅ Paper analysis completed successfully!", "success");
    
  } catch (error) {
    console.error(error);
    showToast("❌ Analysis failed: " + error.message, "error");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Paper";
  }
}

function displayAnalysis(analysis) {
  let body = "";

  const sections = [
    { key: "research_problem", title: "Research Problem" },
    { key: "research_objectives", title: "Research Objectives" },
    { key: "methodology", title: "Methodology" },
    { key: "dataset", title: "Dataset" },
    { key: "evaluation_metrics", title: "Evaluation Metrics" },
    { key: "key_findings", title: "Key Findings" },
    { key: "main_contributions", title: "Main Contributions" },
    { key: "limitations", title: "Limitations" },
    { key: "future_work", title: "Future Work" }
  ];

  sections.forEach(section => {
    const value = analysis[section.key];
    if (value) {
      const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
      body += `
        <div class="analysis-section">
          <h4>${section.title}</h4>
          <p>${displayValue}</p>
        </div>
      `;
    }
  });

  if (analysis.evidence) {
    body += `<h3>Evidence</h3>`;
    Object.entries(analysis.evidence).forEach(([key, evidence]) => {
      if (evidence && evidence.text) {
        body += `
          <div class="analysis-section">
            <h4>${key}</h4>
            <p>"${evidence.text}" (Page ${evidence.page || "N/A"})</p>
          </div>
        `;
      }
    });
  }

  document.getElementById("analysis-body").innerHTML = body;
  document.getElementById("analysis-modal").style.display = "block";
}

async function comparePapers() {
  if (selectedPapers.size < 2) {
    const msg = selectedPapers.size === 0
      ? "⚠️ Please select at least 2 papers using the checkboxes below to compare."
      : "⚠️ Please select at least 1 more paper to compare (2 required).";
    showToast(msg, "warning");
    showToolbarMessage(msg, "hint");
    return;
  }

  const btn = document.getElementById("compare-selected-btn");
  const statusEl = document.getElementById("papers-toolbar-status");
  btn.disabled = true;
  btn.textContent = "⏳ Comparing...";
  showToast(`⚖️ Comparing ${selectedPapers.size} selected papers...`, "info");
  statusEl.textContent = "🔄 Comparing selected papers — this may take a few seconds...";
  statusEl.className = "toolbar-status working";

  try {
    // Step 1: Ensure all selected papers are analyzed first
    const paperIds = Array.from(selectedPapers);
    statusEl.textContent = "🔄 Ensuring all papers are analyzed...";

    for (const pid of paperIds) {
      const paperData = await fetch(`${API_BASE}/api/papers/${pid}`).then(r => r.json());
      if (!paperData.paper.analysis) {
        statusEl.textContent = `🔄 Analyzing "${paperData.paper.title}" first...`;
        showToast(`🧠 Pre-analyzing "${paperData.paper.title}"...`, "info", 2500);
        const analyzeRes = await fetch(`${API_BASE}/api/analyze/${pid}`, { method: "POST" });
        if (!analyzeRes.ok) {
          const err = await analyzeRes.json();
          throw new Error(`Analysis failed for "${paperData.paper.title}": ${err.detail}`);
        }
      }
    }

    // Step 2: Compare
    statusEl.textContent = "🔄 Running multi-paper synthesis...";
    const response = await fetch(`${API_BASE}/api/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(paperIds)
    });
    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || "Comparison failed");

    displayComparison(data.comparison);
    statusEl.textContent = `✅ Comparison complete for ${paperIds.length} papers.`;
    statusEl.className = "toolbar-status success";
    showToast("✅ Multi-paper comparison generated successfully!", "success");

  } catch (error) {
    console.error(error);
    statusEl.textContent = `❌ ${error.message}`;
    statusEl.className = "toolbar-status error";
    showToast(`❌ Comparison failed: ${error.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "⚖️ Compare Selected";
  }
}

function displayComparison(comparison) {
  let body = `<h3>Synthesis</h3><p>${comparison.synthesis || "No synthesis available"}</p>`;

  if (comparison.comparison_table && Array.isArray(comparison.comparison_table)) {
    body += `<h3>Comparison Table</h3>`;
    body += `<table class="comparison-table"><thead><tr>`;

    const headers = Object.keys(comparison.comparison_table[0]);
    headers.forEach(h => {
      body += `<th>${h}</th>`;
    });
    body += `</tr></thead><tbody>`;

    comparison.comparison_table.forEach(row => {
      body += `<tr>`;
      headers.forEach(h => {
        const value = row[h];
        const displayValue = typeof value === 'object' ? JSON.stringify(value) : (value || "N/A");
        body += `<td>${displayValue}</td>`;
      });
      body += `</tr>`;
    });

    body += `</tbody></table>`;
  }

  document.getElementById("comparison-body").innerHTML = body;
  document.getElementById("comparison-modal").style.display = "block";
}

async function detectResearchGaps() {
  if (selectedPapers.size < 2) {
    const msg = selectedPapers.size === 0
      ? "⚠️ Please select at least 2 papers using the checkboxes below to detect research gaps."
      : "⚠️ Please select at least 1 more paper to detect research gaps (2 required).";
    showToast(msg, "warning");
    showToolbarMessage(msg, "hint");
    return;
  }

  const btn = document.getElementById("detect-gaps-btn");
  const statusEl = document.getElementById("papers-toolbar-status");
  btn.disabled = true;
  btn.textContent = "⏳ Detecting...";
  showToast(`🔎 Detecting research gaps across ${selectedPapers.size} papers...`, "info");
  statusEl.textContent = "🔄 Detecting research gaps — analyzing limitations and future work...";
  statusEl.className = "toolbar-status working";

  try {
    const paperIds = Array.from(selectedPapers);

    // Ensure all papers are analyzed first
    for (const pid of paperIds) {
      const paperData = await fetch(`${API_BASE}/api/papers/${pid}`).then(r => r.json());
      if (!paperData.paper.analysis) {
        statusEl.textContent = `🔄 Analyzing "${paperData.paper.title}" first...`;
        showToast(`🧠 Pre-analyzing "${paperData.paper.title}"...`, "info", 2500);
        const analyzeRes = await fetch(`${API_BASE}/api/analyze/${pid}`, { method: "POST" });
        if (!analyzeRes.ok) {
          const err = await analyzeRes.json();
          throw new Error(`Analysis failed for "${paperData.paper.title}": ${err.detail}`);
        }
      }
    }

    statusEl.textContent = "🔄 Identifying candidate research gaps...";
    const response = await fetch(`${API_BASE}/api/research-gaps`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(paperIds)
    });
    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || "Gap detection failed");

    displayResearchGaps(data.research_gaps);
    statusEl.textContent = `✅ Research gap analysis complete.`;
    statusEl.className = "toolbar-status success";
    showToast("✅ Candidate research gaps detected successfully!", "success");

  } catch (error) {
    console.error(error);
    statusEl.textContent = `❌ ${error.message}`;
    statusEl.className = "toolbar-status error";
    showToast(`❌ Gap detection failed: ${error.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "🔎 Detect Research Gaps";
  }
}

function displayResearchGaps(gaps) {
  let body = "";

  if (gaps.research_gaps && Array.isArray(gaps.research_gaps) && gaps.research_gaps.length > 0) {
    gaps.research_gaps.forEach((gap, index) => {
      const supportingPapers = Array.isArray(gap.supporting_papers)
        ? gap.supporting_papers.join(", ")
        : gap.supporting_papers || "N/A";

      body += `
        <div class="gap-item">
          <h4>Gap ${index + 1}: ${gap.gap_statement || "No statement"}</h4>
          <p><strong>Supporting Papers:</strong> ${supportingPapers}</p>
          <p><strong>Evidence:</strong> ${gap.evidence || "N/A"}</p>
          <p><strong>Why It Matters:</strong> ${gap.why_it_matters || "N/A"}</p>
          <p><strong>Research Question:</strong> ${gap.research_question || "N/A"}</p>
          <p><strong>Validation Approach:</strong> ${gap.validation_approach || "N/A"}</p>
          <p><strong>Confidence:</strong> ${gap.confidence || "N/A"} - ${gap.rationale || "N/A"}</p>
        </div>
      `;
    });
  } else {
    body = "<p>No research gaps identified.</p>";
  }

  document.getElementById("gaps-body").innerHTML = body;
  document.getElementById("gaps-modal").style.display = "block";
}

async function generateReport() {
  if (selectedPapers.size < 1) {
    const msg = "⚠️ Please select at least 1 paper using the checkboxes below to generate a report.";
    showToast(msg, "warning");
    showToolbarMessage(msg, "hint");
    return;
  }

  // Show inline query panel instead of prompt()
  const panel = document.getElementById("report-query-panel");
  panel.style.display = "block";
  document.getElementById("report-query-input").focus();
  showToast("📄 Enter your research question for the report below.", "info", 3000);
}

async function submitReport() {
  const query = (document.getElementById("report-query-input").value || "").trim();
  if (!query) {
    showToolbarMessage("⚠️ Please enter a research question first.", "error");
    showToast("⚠️ Please enter a research question first.", "warning");
    return;
  }

  const panel = document.getElementById("report-query-panel");
  panel.style.display = "none";

  const btn = document.getElementById("generate-report-btn");
  const statusEl = document.getElementById("papers-toolbar-status");
  btn.disabled = true;
  btn.textContent = "⏳ Generating...";
  showToast(`📄 Generating literature review for: "${query}"...`, "info");
  statusEl.textContent = "🔄 Generating literature review report...";
  statusEl.className = "toolbar-status working";

  try {
    const paperIds = Array.from(selectedPapers);

    // Ensure all papers are analyzed first
    for (const pid of paperIds) {
      const paperData = await fetch(`${API_BASE}/api/papers/${pid}`).then(r => r.json());
      if (!paperData.paper.analysis) {
        statusEl.textContent = `🔄 Analyzing "${paperData.paper.title}" first...`;
        showToast(`🧠 Pre-analyzing "${paperData.paper.title}"...`, "info", 2500);
        const analyzeRes = await fetch(`${API_BASE}/api/analyze/${pid}`, { method: "POST" });
        if (!analyzeRes.ok) {
          const err = await analyzeRes.json();
          throw new Error(`Analysis failed for "${paperData.paper.title}": ${err.detail}`);
        }
      }
    }

    statusEl.textContent = "🔄 Compiling literature review...";
    const response = await fetch(`${API_BASE}/api/generate-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, paper_ids: paperIds })
    });
    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || "Report generation failed");

    currentReportContent = data.report;
    document.getElementById("report-title").textContent =
      data.report_id ? `Report #${data.report_id} — ${query}` : `Literature Review — ${query}`;
    document.getElementById("report-body").innerHTML =
      `<pre style="white-space:pre-wrap;font-size:0.92rem;line-height:1.7;">${escapeHtml(data.report)}</pre>`;
    document.getElementById("report-modal").style.display = "block";

    statusEl.textContent = `✅ Report generated successfully!`;
    statusEl.className = "toolbar-status success";
    showToast("✅ Literature review report generated successfully!", "success");
    document.getElementById("report-query-input").value = "";

  } catch (error) {
    console.error(error);
    statusEl.textContent = `❌ ${error.message}`;
    statusEl.className = "toolbar-status error";
    showToast(`❌ Report generation failed: ${error.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "📄 Generate Report";
  }
}

function showToolbarMessage(msg, type) {
  const statusEl = document.getElementById("papers-toolbar-status");
  if (statusEl) {
    statusEl.textContent = msg;
    statusEl.className = `toolbar-status ${type}`;
  }
}

function escapeHtml(str) {
  return (str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function downloadReport() {
  if (!currentReportContent) return;
  
  showToast("💾 Downloading report markdown file...", "info", 2500);
  const blob = new Blob([currentReportContent], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "literature_review.md";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Load reports
async function loadReports() {
  const reportsList = document.getElementById("reports-list");
  reportsList.innerHTML = "<p>Loading reports...</p>";

  try {
    const response = await fetch(`${API_BASE}/api/reports`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to load reports");
    }

    reportsList.innerHTML = "";

    if (!data.reports || data.reports.length === 0) {
      reportsList.innerHTML = "<p>No reports generated yet.</p>";
      return;
    }

    data.reports.forEach(report => {
      const item = document.createElement("div");
      item.className = "report-item";
      item.innerHTML = `
        <h3>${report.title}</h3>
        <p class="meta">Created: ${new Date(report.created_at).toLocaleString()}</p>
        <p class="meta">Papers: ${report.paper_ids.length}</p>
        <button class="action-btn" onclick="viewReport(${report.id})">View Report</button>
      `;
      reportsList.appendChild(item);
    });
  } catch (error) {
    console.error(error);
    reportsList.innerHTML = "<p>Failed to load reports.</p>";
    showToast("❌ Failed to load reports list", "error");
  }
}

async function viewReport(reportId) {
  try {
    showToast("📄 Loading report...", "info", 2000);
    const response = await fetch(`${API_BASE}/api/reports/${reportId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to load report");
    }

    currentReportContent = data.report.report_content;
    document.getElementById("report-title").textContent = data.report.title;
    document.getElementById("report-body").innerHTML =
      `<pre style="white-space:pre-wrap;font-size:0.92rem;line-height:1.7;">${escapeHtml(data.report.report_content)}</pre>`;
    document.getElementById("report-modal").style.display = "block";
    showToast("✅ Report loaded", "success", 2000);
    
  } catch (error) {
    console.error(error);
    showToast("❌ Failed to load report: " + error.message, "error");
  }
}

// Modal handling
function setupModals() {
  const closeButtons = document.querySelectorAll('.close-modal');
  closeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.modal').style.display = 'none';
    });
  });

  window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
      e.target.style.display = 'none';
    }
  });
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  checkBackendHealth();
  setupNavigation();
  setupModals();
  
  document.getElementById("search-form").addEventListener("submit", handleSearchSubmit);
  document.getElementById("upload-form").addEventListener("submit", handleUploadSubmit);
  document.getElementById("refresh-papers-btn").addEventListener("click", loadPapers);
  document.getElementById("compare-selected-btn").addEventListener("click", comparePapers);
  document.getElementById("detect-gaps-btn").addEventListener("click", detectResearchGaps);
  document.getElementById("generate-report-btn").addEventListener("click", generateReport);
  document.getElementById("analyze-paper-btn").addEventListener("click", analyzePaper);
  document.getElementById("download-report-btn").addEventListener("click", downloadReport);

  // Inline report query panel
  document.getElementById("submit-report-btn").addEventListener("click", submitReport);
  document.getElementById("cancel-report-btn").addEventListener("click", () => {
    document.getElementById("report-query-panel").style.display = "none";
  });
  document.getElementById("report-query-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") submitReport();
  });
  
  // Paper modal actions
  document.getElementById("view-chunks-btn").addEventListener("click", () => viewPaperChunks(currentPaperId));
  document.getElementById("ask-question-btn").addEventListener("click", openChatbot);

  // Main chat page listeners
  document.getElementById("main-send-chat-btn").addEventListener("click", () => sendChatMessage(false));
  document.getElementById("main-chat-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendChatMessage(false);
  });
  document.getElementById("clear-chat-btn").addEventListener("click", clearMainChat);

  // Modal chat listeners
  document.getElementById("send-chat-btn").addEventListener("click", () => sendChatMessage(true));
  document.getElementById("chat-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendChatMessage(true);
  });

  // Suggestion chips
  document.querySelectorAll(".chat-suggestion-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const prompt = chip.dataset.prompt;
      if (prompt) {
        document.getElementById("main-chat-input").value = prompt;
        sendChatMessage(false);
      }
    });
  });

  // Start on search page
  navigateTo('search');
});

// View paper text chunks
async function viewPaperChunks(paperId) {
  if (!paperId) paperId = currentPaperId;
  if (!paperId) return;

  const modalBody = document.getElementById("chunks-body");
  const modalTitle = document.getElementById("chunks-title");
  modalBody.innerHTML = "<p>Loading text chunks...</p>";
  document.getElementById("chunks-modal").style.display = "block";
  showToast("📑 Loading extracted paper chunks...", "info", 2000);

  try {
    const res = await fetch(`${API_BASE}/api/papers/${paperId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load chunks");

    modalTitle.textContent = `Extracted Chunks: ${data.paper?.title || "Paper"}`;
    if (!data.chunks || data.chunks.length === 0) {
      modalBody.innerHTML = "<p>No text chunks found for this paper.</p>";
      return;
    }

    modalBody.innerHTML = "";
    data.chunks.forEach((c) => {
      const item = document.createElement("div");
      item.className = "chunk-item";
      item.innerHTML = `
        <div class="chunk-header">
          <span>Page ${c.page_number} (Chunk #${c.chunk_index + 1})</span>
          <span>${c.section || "Body"}</span>
        </div>
        <p class="chunk-text">${c.text}</p>
      `;
      modalBody.appendChild(item);
    });
    showToast(`✅ Loaded ${data.chunks.length} paper chunks`, "success", 2000);
  } catch (err) {
    modalBody.innerHTML = `<p style="color: #ef4444;">Error loading chunks: ${err.message || err}</p>`;
    showToast(`❌ Failed to load chunks: ${err.message}`, "error");
  }
}

// Populate the paper selector in the chat view
function populateChatPaperSelect() {
  const select = document.getElementById("chat-paper-select");
  if (!select) return;
  const currentVal = select.value;
  select.innerHTML = '<option value="all">All Uploaded Papers</option>';
  
  allUploadedPapers.forEach(p => {
    if (p.processing_status === "completed") {
      const opt = document.createElement("option");
      opt.value = String(p.id);
      opt.textContent = p.title.length > 55 ? p.title.substring(0, 52) + "..." : p.title;
      select.appendChild(opt);
    }
  });

  if (currentVal && Array.from(select.options).some(o => o.value === currentVal)) {
    select.value = currentVal;
  }
}

// Setup dedicated chat page
function setupChatPage() {
  if (allUploadedPapers.length === 0) {
    loadPapers();
  } else {
    populateChatPaperSelect();
  }

  const chatHistory = document.getElementById("main-chat-history");
  if (!chatHistory.hasChildNodes()) {
    renderChatMessage(
      "bot",
      "Hello! I am your PaperSense Research Assistant. Select a paper above or ask questions across all your uploaded papers. Every answer is grounded directly in the paper with page citations and evidence quotes.",
      "main-chat-history"
    );
  }
  document.getElementById("main-chat-input").focus();
}

function clearMainChat() {
  const container = document.getElementById("main-chat-history");
  if (container) {
    container.innerHTML = "";
    setupChatPage();
  }
}

// Chatbot functionality
function openChatbot() {
  document.getElementById("paper-modal").style.display = "none";
  // Seamlessly navigate to the rich Chat view with the chosen paper pre-selected
  navigateTo('chat');
  const select = document.getElementById("chat-paper-select");
  if (currentPaperId && select) {
    select.value = String(currentPaperId);
  }
  document.getElementById("main-chat-input").focus();
}

async function sendChatMessage(isModal = false) {
  const input = document.getElementById(isModal ? "chat-input" : "main-chat-input");
  const sendBtn = document.getElementById(isModal ? "send-chat-btn" : "main-send-chat-btn");
  const historyContainerId = isModal ? "chat-history" : "main-chat-history";
  const question = input.value.trim();

  if (!question) return;

  const targetPaperVal = isModal
    ? currentPaperId
    : document.getElementById("chat-paper-select").value;

  const paperId = (!targetPaperVal || targetPaperVal === "all") ? null : parseInt(targetPaperVal);

  // Add user message to chat UI
  renderChatMessage("user", question, historyContainerId);
  input.value = "";
  sendBtn.disabled = true;

  // Add typing indicator
  const typingId = "typing-" + Date.now();
  addTypingIndicator(historyContainerId, typingId);

  try {
    const payload = { question: question };
    if (paperId !== null) {
      payload.paper_id = paperId;
    }

    const response = await fetch(`${API_BASE}/api/ask-question`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    removeTypingIndicator(typingId);

    if (!response.ok) {
      let errorMsg = data.detail || "Failed to get answer";
      if (Array.isArray(errorMsg)) {
        errorMsg = errorMsg.map(e => e.msg || JSON.stringify(e)).join("; ");
      } else if (typeof errorMsg === "object") {
        errorMsg = JSON.stringify(errorMsg);
      }
      throw new Error(errorMsg);
    }

    if (data.answer) {
      renderChatMessage("bot", data.answer, historyContainerId);
    } else {
      renderChatMessage("bot", "No answer received from server.", historyContainerId);
    }

  } catch (error) {
    removeTypingIndicator(typingId);
    console.error("Chat error:", error);
    const errorMsg = error.message || String(error);
    renderChatMessage("bot", `Error: ${errorMsg}`, historyContainerId);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

function addTypingIndicator(containerId, typingId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-message bot";
  msgDiv.id = typingId;
  msgDiv.innerHTML = `
    <div class="message-content">
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    </div>
  `;
  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator(typingId) {
  const el = document.getElementById(typingId);
  if (el) el.remove();
}

function renderChatMessage(role, content, containerId = "chat-history") {
  const chatHistory = document.getElementById(containerId);
  if (!chatHistory) return;
  const messageDiv = document.createElement("div");
  messageDiv.className = `chat-message ${role}`;

  if (!content) {
    messageDiv.innerHTML = `<div class="message-content"><p>No content</p></div>`;
  } else if (typeof content === "object") {
    // Structured answer object
    let html = `<div class="message-content">`;
    html += `<p class="answer-text">${content.answer || "No answer provided"}</p>`;

    if (content.evidence && Array.isArray(content.evidence) && content.evidence.length > 0) {
      html += `<div class="evidence-section"><h5>Evidence & Citations:</h5>`;
      content.evidence.forEach((ev) => {
        if (ev && ev.text) {
          html += `
            <div class="evidence-item">
              <p><em>"${ev.text}"</em></p>
              <p class="evidence-meta">Page ${ev.page ?? "N/A"}${ev.relevance ? " • " + ev.relevance : ""}</p>
            </div>
          `;
        }
      });
      html += `</div>`;
    }

    if (content.confidence) {
      html += `<p class="confidence">Confidence: ${content.confidence}</p>`;
    }

    if (content.reasoning) {
      html += `<p class="reasoning"><strong>Reasoning:</strong> ${content.reasoning}</p>`;
    }

    if (content.warning) {
      html += `<p class="evidence-meta" style="color: #f59e0b; margin-top: 6px;">Note: ${content.warning}</p>`;
    }

    html += `</div>`;
    messageDiv.innerHTML = html;
  } else {
    // Plain text string
    messageDiv.innerHTML = `<div class="message-content"><p>${content}</p></div>`;
  }

  chatHistory.appendChild(messageDiv);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}


// =============================================
// Pillar 2: Peer Review Page
// =============================================
async function setupPeerReviewPage() {
  await populatePaperSelect("peer-review-paper-select");
  const btn = document.getElementById("run-peer-review-btn");
  if (btn._peerReviewBound) return;
  btn._peerReviewBound = true;
  btn.addEventListener("click", async () => {
    const paperId = document.getElementById("peer-review-paper-select").value;
    const statusEl = document.getElementById("peer-review-status");
    const resultsEl = document.getElementById("peer-review-results");
    if (!paperId) {
      statusEl.textContent = "Please select a paper first.";
      showToast("⚠️ Please select a paper to run peer review.", "warning");
      return;
    }
    statusEl.textContent = "Running peer review…";
    showToast("🔍 Running adversarial peer review audit...", "info");
    btn.disabled = true;
    resultsEl.innerHTML = "";
    try {
      const res = await fetch(`${API_BASE}/api/peer-review/${paperId}`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Peer review failed");
      statusEl.textContent = "Peer review complete.";
      showToast(`✅ Peer review complete (Score: ${data.review.overall_score || "N/A"}/100)!`, "success");
      renderPeerReview(data.review, resultsEl);
    } catch (err) {
      statusEl.textContent = `Error: ${err.message}`;
      showToast(`❌ Peer review failed: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
    }
  });
}

function renderPeerReview(review, container) {
  const score = review.overall_score ?? "N/A";
  let html = `
    <div class="review-summary-row">
      <div class="overall-score">${score}<span class="score-label">/100</span></div>
      <div class="review-summary-text">${review.summary || ""}</div>
    </div>
    <h3 style="color:var(--text-dim);font-size:0.85rem;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:12px;">Findings</h3>
  `;
  (review.findings || []).forEach(f => {
    const severity = (f.severity || "info").toLowerCase();
    html += `
      <div class="finding-card ${severity}">
        <div class="finding-header">
          <span class="severity-badge">${f.severity || "info"}</span>
          <span class="category-label">${(f.category || "").replace(/_/g, " ")}</span>
        </div>
        <p class="finding-desc">${f.description || ""}</p>
        ${f.evidence_text ? `<p class="finding-evidence">"${f.evidence_text}"</p>` : ""}
      </div>
    `;
  });
  container.innerHTML = html;
}

// =============================================
// Pillar 3: Citations Page
// =============================================
async function setupCitationsPage() {
  await populatePaperSelect("citations-paper-select");
  const btn = document.getElementById("fetch-citations-btn");
  if (btn._citationsBound) return;
  btn._citationsBound = true;
  btn.addEventListener("click", async () => {
    const paperId = document.getElementById("citations-paper-select").value;
    const statusEl = document.getElementById("citations-status");
    const resultsEl = document.getElementById("citations-results");
    if (!paperId) {
      statusEl.textContent = "Please select a paper first.";
      showToast("⚠️ Please select a paper to fetch citations.", "warning");
      return;
    }
    statusEl.textContent = "Fetching citation graph…";
    showToast("📚 Querying Semantic Scholar citation consensus graph...", "info");
    btn.disabled = true;
    resultsEl.innerHTML = "";
    try {
      const res = await fetch(`${API_BASE}/api/citations/${paperId}`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Citation fetch failed");
      const graph = data.citation_graph || {};
      const count = (graph.citations || []).length;

      if (graph.offline_fallback || graph.note) {
        statusEl.textContent = graph.note || "⚡ Displaying citation consensus from document references & local corpus (offline mode).";
        showToast(`⚡ Loaded ${count} consensus citations via Offline Engine!`, "success", 4000);
      } else if (graph.error) {
        statusEl.textContent = `Note: ${graph.error}`;
        showToast(`ℹ️ ${graph.error}`, "warning", 5000);
      } else {
        statusEl.textContent = `Found ${count} related papers via Semantic Scholar.`;
        showToast(`✅ Found ${count} citation graph connections!`, "success");
      }
      renderCitations(graph, resultsEl);
    } catch (err) {
      statusEl.textContent = `Error: ${err.message}`;
      showToast(`❌ Citation lookup failed: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
    }
  });
}

function renderCitations(graph, container) {
  const citations = graph.citations || [];
  if (!citations.length) {
    container.innerHTML = "<p style='color:var(--text-dim)'>No citations found. You can upload additional papers to enable local cross-paper agreement analysis.</p>";
    return;
  }
  let html = "";
  if (graph.offline_fallback) {
    html += `
      <div class="offline-citation-banner">
        <span>⚡ <strong>Offline Consensus Engine:</strong> Sourced from internal document references and local scholarly corpus.</span>
      </div>
    `;
  }
  html += `<h3 style="color:var(--text-dim);font-size:0.85rem;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:12px;">Related Papers &amp; Consensus</h3>`;
  citations.forEach(c => {
    const rel = (c.relationship || "UNRELATED").toUpperCase();
    const authors = (c.authors || []).slice(0, 3).join(", ");
    html += `
      <div class="citation-card">
        <div class="citation-info">
          <div class="citation-title">${c.title || "Untitled"}</div>
          <div class="citation-meta">${authors ? authors + " • " : ""}${c.year || ""}</div>
          ${c.abstract ? `<div class="citation-meta" style="margin-top:4px">${c.abstract}</div>` : ""}
        </div>
        <span class="relationship-badge ${rel}">${rel}</span>
      </div>
    `;
  });
  container.innerHTML = html;
}

// =============================================
// Pillar 5: Hypothesis Page
// =============================================
async function setupHypothesisPage() {
  await populatePaperSelect("hypothesis-paper-select");
  const btn = document.getElementById("generate-hypothesis-btn");
  if (btn._hypothesisBound) return;
  btn._hypothesisBound = true;
  btn.addEventListener("click", async () => {
    const paperId = document.getElementById("hypothesis-paper-select").value;
    const question = document.getElementById("hypothesis-question").value.trim();
    const statusEl = document.getElementById("hypothesis-status");
    const resultsEl = document.getElementById("hypothesis-results");
    if (!paperId) {
      statusEl.textContent = "Please select a paper first.";
      showToast("⚠️ Please select a paper first.", "warning");
      return;
    }
    if (!question) {
      statusEl.textContent = "Please enter a what-if question.";
      showToast("⚠️ Please enter a what-if question.", "warning");
      return;
    }
    statusEl.textContent = "Generating hypothesis…";
    showToast("🔬 Generating grounded hypothesis & experiments...", "info");
    btn.disabled = true;
    resultsEl.innerHTML = "";
    try {
      const res = await fetch(`${API_BASE}/api/hypothesis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper_id: parseInt(paperId), question })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Hypothesis generation failed");
      statusEl.textContent = "Hypothesis generated.";
      showToast("✅ Scientific hypothesis generated successfully!", "success");
      renderHypothesis(data.result, resultsEl);
    } catch (err) {
      statusEl.textContent = `Error: ${err.message}`;
      showToast(`❌ Hypothesis generation failed: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
    }
  });
}

function renderHypothesis(result, container) {
  if (!result) { container.innerHTML = "<p>No result returned.</p>"; return; }

  const outcomesList = (result.predicted_outcomes || []).map(o => `<li>${o}</li>`).join("");
  const experimentsList = (result.suggested_experiments || []).map(e => `<li>${e}</li>`).join("");
  const sectionsList = (result.relevant_sections || [])
    .map(s => `<li><em>"${s.text}"</em>${s.page ? ` — Page ${s.page}` : ""}</li>`).join("");

  container.innerHTML = `
    <div class="hypothesis-result">
      <h3>Hypothesis</h3>
      <p class="hypothesis-text">${result.hypothesis || ""}</p>
    </div>
    ${result.confidence ? `<span class="confidence-badge">Confidence: ${result.confidence}</span>` : ""}
    ${outcomesList ? `<div class="hypothesis-result"><h3>Predicted Outcomes</h3><ul>${outcomesList}</ul></div>` : ""}
    ${experimentsList ? `<div class="hypothesis-result"><h3>Suggested Experiments</h3><ul>${experimentsList}</ul></div>` : ""}
    ${sectionsList ? `<div class="hypothesis-result"><h3>Relevant Sections</h3><ul>${sectionsList}</ul></div>` : ""}
    ${result.limitations ? `<div class="hypothesis-result"><h3>Limitations</h3><p class="hypothesis-text">${result.limitations}</p></div>` : ""}
  `;
}

// =============================================
// Helper: populate a paper <select> by ID
// =============================================
async function populatePaperSelect(selectId) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  try {
    const res = await fetch(`${API_BASE}/api/papers`);
    const data = await res.json();
    const papers = (data.papers || []).filter(p => p.processing_status === "completed");
    // Keep the default option, replace the rest
    sel.innerHTML = '<option value="">-- Select a paper --</option>';
    papers.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.title || p.file_name;
      sel.appendChild(opt);
    });
  } catch (e) {
    // Silently fail — list may be empty
  }
}
