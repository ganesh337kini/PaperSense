# PaperSense: Advanced Multi-Modal Scholarly Intelligence Platform

PaperSense transforms academic document analysis from basic summarization and flat RAG into an **Advanced Multi-Modal Scholarly Intelligence Platform**. It addresses critical open research gaps in scientific document comprehension, adversarial peer review, cross-paper consensus mapping, and counterfactual hypothesis generation.

---

## 🎯 Research Gaps PaperSense Fills

Traditional document summarization and naive RAG architectures suffer from five fundamental research and engineering limitations when applied to scientific literature:

| Research Gap in Existing Tools | The Problem | How PaperSense Solves It |
|---|---|---|
| **1. Flat Text Chunking & Layout Blindness** | Standard chunkers destroy column flow, mathematical equations, Markdown table structures, and diagrams. | **Layout-Aware Multi-Modal Parsing** with PyMuPDF `rawdict`, equation classification ($\LaTeX$), structured table preservation, and Vision-LLM integration (GPT-4o) for figures and charts. |
| **2. Uncritical, Passive Summarization** | Standard AI agents accept claims at face value without validating scientific methodology or experimental rigor. | **Adversarial Peer Review Agent**: Automated critical audit engine evaluating baseline fairness, missing ablation studies, hidden assumptions, data leakage, and statistical significance. |
| **3. Isolated Document Silos** | Literature tools treat papers in isolation without understanding whether newer works replicate, support, or refute prior findings. | **Semantic Citation & Consensus Graph**: Dynamic query engine (Semantic Scholar, CrossRef, and local offline consensus fallback) that classifies relationships as `SUPPORTS`, `CONTRADICTS`, `EXTENDS`, or `UNRELATED`. |
| **4. Hallucinations & Unverifiable Citations** | Standard LLM outputs offer vague quotes that cannot be quickly visually located in dense multi-page PDFs. | **Verifiable Bounding-Box Grounding**: Every evidence citation returns exact coordinates `(bbox_x0, bbox_y0, bbox_x1, bbox_y1, page)` mapped to the PDF viewer for zero-hallucination verification. |
| **5. Static Q&A vs. Dynamic Inquiry** | Researchers can only ask about what is written, not explore unexplored experimental configurations. | **Hypothesis Generation & "What-If" Simulator**: Agentic brainstorming sandbox allowing researchers to simulate modified experimental setups, predict outcomes, and plan ablation studies. |

---

## 🚀 Key Features & Architecture Pillars

### 🗺️ Pillar 1: Layout-Aware Multi-Modal Parser & Vision-LLM
- **Block-Level Geometric Extraction**: Bounding-box coordinate extraction per span using PyMuPDF `rawdict`.
- **Heuristic Block Classification**: Classifies document blocks into `text`, `equation` (LaTeX detection and mathematical Unicode symbols), `table` (multi-column grids), and `figure` (image blocks).
- **Vision-LLM Figure Explainer**: Extracts charts and diagrams as high-resolution images and uses GPT-4o vision to describe trends, labels, and architectural workflows.
- **Section Detection**: Automatically identifies paper sections (`Abstract`, `Methodology`, `Results`, `Limitations`, `References`).

### 🔬 Pillar 2: Adversarial Peer Review Agent (Critical Critique Engine)
- **Scientific Rigor Audit**: Evaluates uploaded papers across 6 critical dimensions:
  - **Baseline Fairness**: Detects missing comparisons against state-of-the-art baselines.
  - **Ablation Studies**: Verifies if architectural components are isolated and validated.
  - **Hidden Assumptions**: Surfaces unproven presuppositions that need empirical justification.
  - **Data Leakage & Contamination**: Flags train-test overlaps, target leakage, and improper validation splits.
  - **Statistical Rigor**: Assesses whether p-values, confidence intervals, or standard deviations are reported.
- **Severity Scoring**: Returns overall rigor scores (0–100) and severity-tagged findings (`critical`, `warning`, `info`).
- **Offline & LLM Modes**: Fully operational offline via pattern heuristics, with high-depth evaluation when configured with OpenAI.

### 📚 Pillar 3: Semantic Citation & Agreement/Contradiction Graph
- **Dynamic Cross-Paper Consensus**: Analyzes citation networks to classify relationships as:
  - 🟢 `SUPPORTS`: Confirms or replicates findings.
  - 🔵 `EXTENDS`: Builds upon, generalizes, or adapts the methodology.
  - 🔴 `CONTRADICTS`: Challenges, refutes, or uncovers edge-case limitations.
  - ⚪ `UNRELATED`: Foundational or background mention.
- **Dual Engine (Online + Offline)**:
  - *Online*: Queries Semantic Scholar and CrossRef APIs with academic headers.
  - *Offline Consensus Fallback*: If external APIs are unavailable, extracts internal references directly from the paper and performs cross-paper consensus comparison with all other papers uploaded in the local library.

### 📍 Pillar 4: Verifiable Bounding-Box Grounding & PDF Serving
- **Zero-Hallucination Evidence**: Chat responses and analysis reports return exact bounding box coordinates:
  ```json
  {
    "text": "Direct quote from paper...",
    "page": 3,
    "bbox": {"x0": 54.0, "y0": 210.5, "x1": 450.2, "y1": 242.0, "page": 3}
  }
  ```
- **Direct PDF Serving**: Built-in endpoint (`GET /api/papers/{id}/pdf`) for serving raw documents with highlight overlays.

### 💡 Pillar 5: Hypothesis Generation & "What-If" Experiment Simulator
- **Counterfactual Experimentation**: Test hypothetical research conditions (e.g. *"What happens if we swap the transformer attention mechanism with a state-space model based on Section 3?"*).
- **Grounded Brainstorming**: Retrieves relevant passages, generates testable scientific hypotheses, predicts potential metric shifts, and suggests step-by-step experiment validation protocols.

### 💬 Interactive Research Assistant Chat & Chunks Inspector
- **Targeted & Corpus Q&A**: Chat with a single paper or query across all uploaded papers simultaneously.
- **Chunks Inspector Modal**: Inspect all extracted text passages with page numbers, chunk IDs, and bounding-box coordinates.
- **Modern Toast & Feedback Notifications**: Immediate interactive feedback and status banners across all actions (Compare, Detect Gaps, Generate Report, Upload, Search, and Analysis).

---

## 🛠️ System Architecture

```
                  ┌───────────────────────────────────────────────┐
                  │            PaperSense Web Frontend            │
                  │   (Vanilla ES6+, CSS Variables, Dark Theme)   │
                  └───────────────────────┬───────────────────────┘
                                          │ REST API
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │             FastAPI Backend Engine            │
                  └───────┬───────────────────────────────┬───────┘
                          │                               │
        ┌─────────────────┴─────────────┐   ┌─────────────┴─────────────────┐
        │  Document & Intelligence APIs │   │ Multi-Modal Scholarly Engine  │
        ├───────────────────────────────┤   ├───────────────────────────────┤
        │ • Upload & PDF Serving        │   │ • LayoutParser (PyMuPDF)      │
        │ • Research Paper Search       │   │ • VisionService (GPT-4o)      │
        │ • Paper Analysis & Comparison │   │ • PeerReviewAgent             │
        │ • RAG Q&A (Grounding & BBox)  │   │ • CitationService (Graph/Cons)│
        │ • Literature Review Reports   │   │ • HypothesisAgent (What-If)   │
        └───────────────┬───────────────┘   └───────────────┬───────────────┘
                        │                                   │
        ┌───────────────┴───────────────┐   ┌───────────────┴───────────────┐
        │       Relational Storage      │   │         Vector Store          │
        ├───────────────────────────────┤   ├───────────────────────────────┤
        │ • SQLite (zero-config dev)    │   │ • FAISS Vector Store          │
        │ • PostgreSQL (production)     │   │ • all-MiniLM-L6-v2 Embeddings │
        │ • SQLAlchemy Models & Schema  │   │ • Metadata & BBox Indexing    │
        └───────────────────────────────┘   └───────────────────────────────┘
```

---

## 📦 Installation & Setup

### Prerequisites
- **Python 3.10 to 3.14**
- Modern Web Browser (Chrome, Safari, Firefox, Edge)

### Quick Start (Zero-Config SQLite)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ganesh337kini/PaperSense.git
   cd PaperSense
   ```

2. **Set up the Python Virtual Environment**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```
   *(Optional)* Edit `backend/.env` to configure your OpenAI API key or Semantic Scholar API key:
   ```env
   OPENAI_API_KEY="your-openai-api-key"
   OPENAI_MODEL="gpt-4o-mini"
   # Optional for higher rate limits on live online citations:
   SEMANTIC_SCHOLAR_API_KEY=""
   # Defaults to SQLite dev database automatically:
   DATABASE_URL="sqlite:///papersense.db"
   ```

4. **Run the Application**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

5. **Open in Browser**:
   Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) (Interactive Swagger documentation available at `http://127.0.0.1:8000/docs`).

---

## 📡 API Reference

### 1. Document Management & Layout
- `POST /api/upload`: Upload PDF, extract layout-aware chunks with bounding boxes, index vectors in FAISS.
- `GET /api/papers`: List all uploaded papers and processing statuses.
- `GET /api/papers/{id}`: Get paper details and chunk metadata (page numbers, bounding boxes).
- `GET /api/papers/{id}/pdf`: Serve raw PDF file for in-browser viewer and coordinate highlighting.
- `DELETE /api/papers/{id}`: Delete paper and remove its FAISS embeddings.

### 2. Scholarly Intelligence & Agent Modules
- `POST /api/peer-review/{paper_id}`: Run adversarial peer review audit (baseline fairness, missing ablations, hidden assumptions, data leakage, statistical score).
- `POST /api/citations/{paper_id}`: Build dynamic citation consensus graph (Semantic Scholar/CrossRef with automatic offline local corpus fallback).
- `POST /api/hypothesis`: Generate testable scientific hypothesis and experimental roadmap from a "what-if" scenario.
- `POST /api/ask-question`: Grounded RAG Q&A with evidence quotes, confidence score, and bounding-box citations.
- `POST /api/analyze/{paper_id}`: Comprehensive paper analysis (objectives, methodology, dataset, findings, limitations).
- `POST /api/compare`: Multi-paper comparison table and cross-paper synthesis.
- `POST /api/research-gaps`: Identify candidate literature research gaps from analyzed papers.
- `POST /api/generate-report`: Compile full literature review report in Markdown with references.
- `GET /api/reports`: List all generated literature review reports.
- `GET /api/reports/{id}`: Retrieve a specific generated report.

### 3. Search & Health
- `GET /api/search`: Query live OpenAlex academic research papers with open-access and sorting filters.
- `GET /api/health`: Backend liveness check.
- `GET /api/db-health`: Database connectivity check and table inspector.

---

## 🧪 Testing

PaperSense includes a complete automated test suite verifying health, database connectivity, validation schemas, single-paper Q&A, and cross-paper RAG retrieval:

```bash
cd backend
HF_HUB_OFFLINE=1 PYTHONPATH=. venv/bin/pytest tests/ -v
```

---

## 📄 License & Credits

Developed as an academic research platform for AI-powered scientific discovery.
- **Core Technologies**: FastAPI, PyMuPDF, FAISS, Sentence-Transformers, SQLAlchemy, OpenAI.
- **Repository**: [https://github.com/ganesh337kini/PaperSense](https://github.com/ganesh337kini/PaperSense)
