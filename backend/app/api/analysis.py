"""
analysis.py
API endpoints for paper analysis, comparison, and research gap detection.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
from datetime import datetime

from app.database import get_db
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.research_query import ResearchQuery
from app.models.report import Report
from app.services.llm_service import LLMService
from app.services.report_service import ReportService
from app.services.embedding_service import embedding_service
from app.services.peer_review_agent import PeerReviewAgent
from app.services.citation_service import CitationService
from app.services.hypothesis_agent import HypothesisAgent

router = APIRouter()
llm_service = LLMService()
report_service = ReportService()
peer_review_agent = PeerReviewAgent()
citation_service = CitationService()
hypothesis_agent = HypothesisAgent()


class AskQuestionRequest(BaseModel):
    paper_id: Optional[int] = None
    question: str


class SemanticSearchRequest(BaseModel):
    query: str
    paper_ids: Optional[List[int]] = None
    top_k: int = 5


class GenerateReportRequest(BaseModel):
    query: str
    paper_ids: List[int]


class HypothesisRequest(BaseModel):
    paper_id: int
    question: str


@router.post("/analyze/{paper_id}")
def analyze_paper(paper_id: int, db: Session = Depends(get_db)):
    """
    Analyze a single research paper using LLM.
    Generates structured analysis with evidence citations.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if paper.processing_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Paper processing status is {paper.processing_status}. Cannot analyze."
        )
    
    # Get chunks
    chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == paper_id).all()
    
    if not chunks:
        raise HTTPException(status_code=400, detail="No text chunks found for this paper")
    
    # Prepare chunks for analysis
    chunks_data = [
        {
            "text": c.text,
            "page_number": c.page_number,
            "section": c.section
        }
        for c in chunks
    ]
    
    try:
        # Run LLM analysis
        analysis = llm_service.analyze_paper(chunks_data)
        
        # Store analysis
        paper.analysis = json.dumps(analysis)
        paper.analysis_date = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "paper_id": paper_id,
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/compare")
def compare_papers(paper_ids: List[int], db: Session = Depends(get_db)):
    """
    Compare multiple research papers.
    Generates a comparison table and synthesis.
    """
    if len(paper_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 papers required for comparison")
    
    # Get papers
    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
    
    if len(papers) != len(paper_ids):
        raise HTTPException(status_code=404, detail="One or more papers not found")
    
    # Check if all papers have analysis
    papers_data = []
    for paper in papers:
        if not paper.analysis:
            raise HTTPException(
                status_code=400,
                detail=f"Paper '{paper.title}' has not been analyzed yet. Please analyze it first."
            )
        
        papers_data.append({
            "title": paper.title,
            "year": paper.year,
            "analysis": json.loads(paper.analysis)
        })
    
    try:
        # Run comparison
        comparison = llm_service.compare_papers(papers_data)
        
        return {
            "status": "success",
            "comparison": comparison
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/research-gaps")
def detect_research_gaps(paper_ids: List[int], db: Session = Depends(get_db)):
    """
    Detect candidate research gaps from multiple papers.
    Analyzes limitations and future work across papers.
    """
    if len(paper_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 papers required for gap detection")
    
    # Get papers
    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
    
    if len(papers) != len(paper_ids):
        raise HTTPException(status_code=404, detail="One or more papers not found")
    
    # Check if all papers have analysis
    papers_data = []
    for paper in papers:
        if not paper.analysis:
            raise HTTPException(
                status_code=400,
                detail=f"Paper '{paper.title}' has not been analyzed yet. Please analyze it first."
            )
        
        papers_data.append({
            "title": paper.title,
            "analysis": json.loads(paper.analysis)
        })
    
    try:
        # Detect research gaps
        gaps = llm_service.detect_research_gaps(papers_data)
        
        return {
            "status": "success",
            "research_gaps": gaps
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research gap detection failed: {str(e)}")


@router.post("/ask-question")
def ask_question(
    req: AskQuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Answer a specific question about a paper (or across all uploaded papers) using LLM / RAG.
    Returns the answer with evidence citations.
    """
    target_paper_id = req.paper_id
    target_question = (req.question or "").strip()

    if not target_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if target_paper_id is not None:
        paper = db.query(Paper).filter(Paper.id == target_paper_id).first()

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        if paper.processing_status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Paper processing status is {paper.processing_status}. Cannot answer questions."
            )

        # Get chunks
        chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == target_paper_id).order_by(PaperChunk.chunk_index).all()

        if not chunks:
            raise HTTPException(status_code=400, detail="No text chunks found for this paper")

        # Use semantic search to identify most relevant chunks for this specific question
        chunks_by_index = {c.chunk_index: c for c in chunks}
        search_results = embedding_service.search(target_question, top_k=6, paper_ids=[target_paper_id])

        ranked_chunks = []
        seen_indices = set()
        for res in search_results:
            c_idx = res.get("chunk_id")
            if c_idx in chunks_by_index and c_idx not in seen_indices:
                seen_indices.add(c_idx)
                c = chunks_by_index[c_idx]
                ranked_chunks.append({
                    "text": c.text,
                    "page_number": c.page_number,
                    "section": c.section,
                    "bbox_x0": c.bbox_x0,
                    "bbox_y0": c.bbox_y0,
                    "bbox_x1": c.bbox_x1,
                    "bbox_y1": c.bbox_y1,
                })

        # Append additional chunks if needed
        if len(ranked_chunks) < 3:
            for c in chunks:
                if c.chunk_index not in seen_indices:
                    ranked_chunks.append({
                        "text": c.text,
                        "page_number": c.page_number,
                        "section": c.section,
                        "bbox_x0": c.bbox_x0,
                        "bbox_y0": c.bbox_y0,
                        "bbox_x1": c.bbox_x1,
                        "bbox_y1": c.bbox_y1,
                    })
                    seen_indices.add(c.chunk_index)
                    if len(ranked_chunks) >= 6:
                        break

        try:
            answer = llm_service.answer_question(target_question, ranked_chunks, paper.title)

            return {
                "status": "success",
                "paper_id": target_paper_id,
                "paper_title": paper.title,
                "question": target_question,
                "answer": answer
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Question answering failed: {str(e)}")

    else:
        # Question across all completed papers
        completed_papers = db.query(Paper).filter(Paper.processing_status == "completed").all()
        if not completed_papers:
            raise HTTPException(status_code=400, detail="No completed papers found. Please upload a PDF first.")

        paper_map = {p.id: p for p in completed_papers}
        search_results = embedding_service.search(target_question, top_k=6, paper_ids=list(paper_map.keys()))

        ranked_chunks = []
        titles_used = set()
        for res in search_results:
            p_id = res.get("paper_id")
            c_idx = res.get("chunk_id")
            if p_id in paper_map:
                chunk = db.query(PaperChunk).filter(
                    PaperChunk.paper_id == p_id,
                    PaperChunk.chunk_index == c_idx
                ).first()
                if chunk:
                    ranked_chunks.append({
                        "text": chunk.text,
                        "page_number": chunk.page_number,
                        "section": chunk.section
                    })
                    titles_used.add(paper_map[p_id].title)

        if not ranked_chunks:
            # Fallback to chunks from first available paper
            first_paper = completed_papers[0]
            chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == first_paper.id).limit(6).all()
            ranked_chunks = [{"text": c.text, "page_number": c.page_number, "section": c.section} for c in chunks]
            titles_used.add(first_paper.title)

        title_summary = ", ".join(list(titles_used)[:3])
        try:
            answer = llm_service.answer_question(target_question, ranked_chunks, title_summary)

            return {
                "status": "success",
                "paper_id": None,
                "paper_title": title_summary,
                "question": target_question,
                "answer": answer
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Question answering failed: {str(e)}")


@router.post("/semantic-search")
def semantic_search(
    req: SemanticSearchRequest
):
    """
    Search for relevant passages using semantic similarity.
    Can filter by specific papers.
    """
    actual_query = (req.query or "").strip()
    if not actual_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        results = embedding_service.search(actual_query, top_k=req.top_k, paper_ids=req.paper_ids)
        
        return {
            "status": "success",
            "query": actual_query,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.post("/generate-report")
def generate_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a complete literature review report.
    Includes analysis, comparison, and research gaps.
    """
    actual_query = (req.query or "").strip()
    if not actual_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not req.paper_ids or len(req.paper_ids) < 1:
        raise HTTPException(status_code=400, detail="At least 1 paper required")
    
    # Get papers
    papers = db.query(Paper).filter(Paper.id.in_(req.paper_ids)).all()
    
    if len(papers) != len(req.paper_ids):
        raise HTTPException(status_code=404, detail="One or more papers not found")
    
    # Ensure all papers are analyzed
    for paper in papers:
        if not paper.analysis:
            raise HTTPException(
                status_code=400,
                detail=f"Paper '{paper.title}' has not been analyzed yet."
            )
    
    try:
        # Prepare data
        papers_data = []
        for paper in papers:
            papers_data.append({
                "id": paper.id,
                "title": paper.title,
                "year": paper.year,
                "doi": paper.doi,
                "url": paper.url,
                "analysis": json.loads(paper.analysis)
            })
        
        # Generate comparison and gaps
        comparison = llm_service.compare_papers(papers_data)
        gaps = llm_service.detect_research_gaps(papers_data)
        
        # Generate report
        report_markdown = report_service.generate_report(
            query=actual_query,
            papers=papers_data,
            comparison=comparison,
            research_gaps=gaps,
            retrieval_date=datetime.utcnow().strftime("%Y-%m-%d")
        )
        
        # Save research query
        research_query = ResearchQuery(query=actual_query)
        db.add(research_query)
        db.commit()
        db.refresh(research_query)
        
        # Save report
        report = Report(
            query_id=research_query.id,
            title=f"Literature Review: {actual_query}",
            report_content=report_markdown,
            paper_ids=json.dumps(req.paper_ids)
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return {
            "status": "success",
            "report_id": report.id,
            "query_id": research_query.id,
            "report": report_markdown,
            "comparison": comparison,
            "research_gaps": gaps
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/reports")
def list_reports(db: Session = Depends(get_db)):
    """List all generated reports."""
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    
    return {
        "status": "success",
        "reports": [
            {
                "id": r.id,
                "title": r.title,
                "query_id": r.query_id,
                "created_at": r.created_at.isoformat(),
                "paper_ids": json.loads(r.paper_ids) if r.paper_ids else []
            }
            for r in reports
        ]
    }


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get a specific report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "status": "success",
        "report": {
            "id": report.id,
            "title": report.title,
            "query_id": report.query_id,
            "report_content": report.report_content,
            "paper_ids": json.loads(report.paper_ids) if report.paper_ids else [],
            "created_at": report.created_at.isoformat()
        }
    }



# ---- Pillar 2: Peer Review ----

@router.post("/peer-review/{paper_id}")
def run_peer_review(paper_id: int, db: Session = Depends(get_db)):
    """Run an adversarial peer review on a paper."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.processing_status != "completed":
        raise HTTPException(status_code=400, detail="Paper not ready")
    chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == paper_id).all()
    chunks_data = [
        {"text": c.text, "page_number": c.page_number, "section": c.section}
        for c in chunks
    ]
    try:
        review = peer_review_agent.run_peer_review(paper.title, chunks_data)
        return {
            "status": "success",
            "paper_id": paper_id,
            "paper_title": paper.title,
            "review": review,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Peer review failed: {str(e)}")


# ---- Pillar 3: Citation Graph ----

@router.post("/citations/{paper_id}")
def get_citation_graph(paper_id: int, db: Session = Depends(get_db)):
    """Build a semantic citation graph for a paper."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    abstract = ""
    if paper.analysis:
        import json as _json
        try:
            a = _json.loads(paper.analysis)
            abstract = a.get("research_problem", "") + " " + a.get("key_findings", "")
        except Exception:
            pass
    try:
        client = llm_service.client if not llm_service.mock_mode else None
        graph = citation_service.build_citation_graph(paper.title, abstract, client)
        return {"status": "success", "paper_id": paper_id, "citation_graph": graph}
    except Exception as e:
        return {
            "status": "partial",
            "paper_id": paper_id,
            "citation_graph": {
                "citations": [],
                "graph_edges": [],
                "error": str(e),
            },
        }


# ---- Pillar 5: Hypothesis Generation ----

@router.post("/hypothesis")
def generate_hypothesis(req: HypothesisRequest, db: Session = Depends(get_db)):
    """Generate a scientific hypothesis based on a what-if question about a paper."""
    paper = db.query(Paper).filter(Paper.id == req.paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.processing_status != "completed":
        raise HTTPException(status_code=400, detail="Paper not ready")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == req.paper_id).all()
    chunks_data = [
        {"text": c.text, "page_number": c.page_number, "section": c.section}
        for c in chunks
    ]
    try:
        result = hypothesis_agent.generate_hypothesis(paper.title, chunks_data, req.question)
        return {
            "status": "success",
            "paper_id": req.paper_id,
            "paper_title": paper.title,
            "question": req.question,
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hypothesis generation failed: {str(e)}")
