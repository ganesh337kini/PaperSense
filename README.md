# PaperSense: Intelligent Research Paper Analysis System

PaperSense is an AI-powered research paper analysis platform that helps researchers search, analyze, compare, and generate literature reviews from academic papers.

## Features

- **Academic Paper Search**: Search for papers using OpenAlex API with filters for year, open-access status, and sorting options
- **PDF Upload & Processing**: Upload research paper PDFs with automatic text extraction and chunking
- **Semantic Search**: Find relevant passages using sentence-transformers embeddings and FAISS
- **AI-Powered Analysis**: Generate structured paper analysis using OpenAI GPT models
- **Multi-Paper Comparison**: Compare multiple papers with synthesis and comparison tables
- **Research Gap Detection**: Identify candidate research gaps from analyzed papers
- **Literature Review Reports**: Generate comprehensive Markdown reports with citations

## Architecture

### Backend
- **Framework**: FastAPI with Python
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Embeddings**: Sentence-Transformers with FAISS vector storage
- **LLM**: OpenAI GPT-4o-mini for analysis
- **PDF Processing**: PyMuPDF for text extraction

### Frontend
- **Technologies**: HTML, CSS, JavaScript (vanilla)
- **Design**: Dark theme with responsive layout

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 12 or higher
- OpenAI API key (for AI analysis features)

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd /Users/ganesh/Downloads/PaperSense\ 2/backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and fill in your values:
   # - OPENAI_API_KEY: Your OpenAI API key
   # - DATABASE_URL: PostgreSQL connection string
   ```

5. **Set up PostgreSQL database**:
   ```bash
   # Create database
   createdb papersense
   
   # Or using psql:
   psql -U postgres
   CREATE DATABASE papersense;
   \q
   ```

6. **Start the server**:
   ```bash
   uvicorn app.main:app --reload
   ```

The backend will be available at `http://127.0.0.1:8000`

### Frontend Setup

The frontend is served statically by the FastAPI backend. No additional setup is required.

## Usage

### 1. Search for Papers

- Navigate to the Search page
- Enter a research topic or keywords
- Use filters for open-access papers and sorting options
- Results include title, authors, abstract, citations, and links

### 2. Upload PDFs

- Navigate to the Upload page
- Select a PDF research paper (max 50MB)
- The system will:
  - Extract text with page numbers
  - Detect image-only PDFs (requires OCR)
  - Chunk text with overlap for semantic search
  - Generate embeddings for retrieval

### 3. Analyze Papers

- Navigate to My Papers
- Click on a paper to view details
- Click "Analyze Paper" to generate structured analysis including:
  - Research problem and objectives
  - Methodology and dataset
  - Key findings and contributions
  - Limitations and future work
  - Evidence with page references

### 4. Compare Papers

- Select 2 or more papers using checkboxes
- Click "Compare Selected"
- View comparison table and synthesis

### 5. Detect Research Gaps

- Select 2 or more analyzed papers
- Click "Detect Research Gaps"
- Review candidate gaps with evidence and confidence levels

### 6. Generate Reports

- Select 1 or more analyzed papers
- Click "Generate Report"
- Enter a research question
- View and download the Markdown literature review

## API Endpoints

### Search
- `GET /api/search` - Search academic papers (OpenAlex)

### Upload & Papers
- `POST /api/upload` - Upload PDF paper
- `GET /api/papers` - List uploaded papers
- `GET /api/papers/{id}` - Get paper details
- `DELETE /api/papers/{id}` - Delete paper

### Analysis
- `POST /api/analyze/{paper_id}` - Analyze a paper
- `POST /api/compare` - Compare multiple papers
- `POST /api/research-gaps` - Detect research gaps
- `POST /api/semantic-search` - Semantic search in papers

### Reports
- `POST /api/generate-report` - Generate literature review
- `GET /api/reports` - List reports
- `GET /api/reports/{id}` - Get report

### Health
- `GET /api/health` - Backend health check
- `GET /api/db-health` - Database health check

## Database Schema

### Tables
- **users**: User accounts (for future authentication)
- **papers**: Paper metadata and processing status
- **paper_chunks**: Text chunks with page numbers and sections
- **research_queries**: Search/query history
- **reports**: Generated literature reviews

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `True` |
| `OPENAI_API_KEY` | OpenAI API key | Required for analysis |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/papersense` |
| `EMBEDDING_MODEL` | Sentence-transformers model | `sentence-transformers/all-MiniLM-L6-v2` |
| `MAX_UPLOAD_SIZE_MB` | Max PDF upload size | `50` |
| `UPLOAD_DIR` | Directory for uploaded PDFs | `uploads` |

## Limitations

- **OCR Support**: Image-only PDFs are detected but not processed (OCR not implemented)
- **Database**: Requires PostgreSQL; no SQLite fallback
- **LLM Costs**: Analysis features require OpenAI API key and incur costs
- **File Size**: Maximum 50MB per PDF upload
- **Concurrent Processing**: PDF processing is synchronous (may block for large files)

## Known Issues

- PostgreSQL must be installed and running for full functionality
- Without PostgreSQL, the app will run but database features won't work
- Embedding index is stored locally (faiss_index.bin) and not backed up automatically

## Future Enhancements

- User authentication and multi-tenancy
- Asynchronous PDF processing with Celery
- OCR support for scanned PDFs
- PDF export for reports
- Citation management
- Collaboration features
- Advanced search filters

## Testing

Run tests with pytest:

```bash
cd backend
pytest tests/
```

## License

This is a final year project for academic purposes.

## Support

For issues or questions, please refer to the API documentation at `/docs` when the server is running.
