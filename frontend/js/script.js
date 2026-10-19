const API_BASE = "";

// State management
let selectedPapers = new Set();
let currentPaperId = null;
let currentReportContent = null;

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
    return;
  }

  statusLine.textContent = "Uploading and processing PDF...";
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
  
  const count = selectedPapers.size;
  
  compareBtn.disabled = count < 2;
  gapsBtn.disabled = count < 2;
  reportBtn.disabled = count < 1;
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
    alert("Failed to load paper details");
  }
}

async function analyzePaper() {
  if (!currentPaperId) return;
  
  const analyzeBtn = document.getElementById("analyze-paper-btn");
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing...";
  
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
    
  } catch (error) {
    console.error(error);
    alert("Analysis failed: " + error.message);
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
    if (analysis[section.key]) {
      body += `
        <div class="analysis-section">
          <h4>${section.title}</h4>
          <p>${analysis[section.key]}</p>
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
  if (selectedPapers.size < 2) return;
  
  const btn = document.getElementById("compare-selected-btn");
  btn.disabled = true;
  btn.textContent = "Comparing...";
  
  try {
    const response = await fetch(`${API_BASE}/api/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Array.from(selectedPapers))
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Comparison failed");
    }

    displayComparison(data.comparison);
    
  } catch (error) {
    console.error(error);
    alert("Comparison failed: " + error.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Compare Selected";
  }
}

function displayComparison(comparison) {
  let body = `<h3>Synthesis</h3><p>${comparison.synthesis || "No synthesis available"}</p>`;
  
  if (comparison.comparison_table) {
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
        body += `<td>${row[h] || "N/A"}</td>`;
      });
      body += `</tr>`;
    });
    
    body += `</tbody></table>`;
  }
  
  document.getElementById("comparison-body").innerHTML = body;
  document.getElementById("comparison-modal").style.display = "block";
}

async function detectResearchGaps() {
  if (selectedPapers.size < 2) return;
  
  const btn = document.getElementById("detect-gaps-btn");
  btn.disabled = true;
  btn.textContent = "Detecting gaps...";
  
  try {
    const response = await fetch(`${API_BASE}/api/research-gaps`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Array.from(selectedPapers))
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Gap detection failed");
    }

    displayResearchGaps(data.research_gaps);
    
  } catch (error) {
    console.error(error);
    alert("Gap detection failed: " + error.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Detect Research Gaps";
  }
}

function displayResearchGaps(gaps) {
  let body = "";
  
  if (gaps.research_gaps && gaps.research_gaps.length > 0) {
    gaps.research_gaps.forEach((gap, index) => {
      body += `
        <div class="gap-item">
          <h4>Gap ${index + 1}: ${gap.gap_statement}</h4>
          <p><strong>Supporting Papers:</strong> ${gap.supporting_papers.join(", ")}</p>
          <p><strong>Evidence:</strong> ${gap.evidence}</p>
          <p><strong>Why It Matters:</strong> ${gap.why_it_matters}</p>
          <p><strong>Research Question:</strong> ${gap.research_question}</p>
          <p><strong>Validation Approach:</strong> ${gap.validation_approach}</p>
          <p><strong>Confidence:</strong> ${gap.confidence} - ${gap.rationale}</p>
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
  if (selectedPapers.size < 1) return;
  
  const query = prompt("Enter research question for the report:");
  if (!query) return;
  
  const btn = document.getElementById("generate-report-btn");
  btn.disabled = true;
  btn.textContent = "Generating...";
  
  try {
    const response = await fetch(`${API_BASE}/api/generate-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: query,
        paper_ids: Array.from(selectedPapers)
      })
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Report generation failed");
    }

    currentReportContent = data.report;
    document.getElementById("report-title").textContent = data.report_id ? `Report #${data.report_id}` : "Literature Review Report";
    document.getElementById("report-body").textContent = data.report;
    document.getElementById("report-modal").style.display = "block";
    
  } catch (error) {
    console.error(error);
    alert("Report generation failed: " + error.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Report";
  }
}

function downloadReport() {
  if (!currentReportContent) return;
  
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
  }
}

async function viewReport(reportId) {
  try {
    const response = await fetch(`${API_BASE}/api/reports/${reportId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to load report");
    }

    currentReportContent = data.report.report_content;
    document.getElementById("report-title").textContent = data.report.title;
    document.getElementById("report-body").textContent = data.report.report_content;
    document.getElementById("report-modal").style.display = "block";
    
  } catch (error) {
    console.error(error);
    alert("Failed to load report");
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
  
  // Start on search page
  navigateTo('search');
});
