"""
analysis.py
API endpoints for paper analysis, comparison, and research gap detection.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import json

from app.database import get_db
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.research_query import ResearchQuery
from app.models.report import Report
from app.services.llm_service import LLMService
from app.services.report_service import ReportService
from app.services.embedding_service import EmbeddingService
from datetime import datetime

router = APIRouter()
llm_service = LLMService()
report_service = ReportService()
embedding_service = EmbeddingService()


@router.post("/analyze/{paper_id}")
def analyze_paper(paper_id: int, db: Session = Depends(get_db)):
    """
    Analyze a single research paper using LLM.
    Generates structured analysis with evidence citations.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if paper.processing_status.value != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Paper processing status is {paper.processing_status.value}. Cannot analyze."
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


@router.post("/semantic-search")
def semantic_search(query: str, paper_ids: List[int] = None, top_k: int = 5):
    """
    Search for relevant passages using semantic similarity.
    Can filter by specific papers.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # Load index
        if not embedding_service.load_index():
            return {
                "status": "success",
                "results": [],
                "message": "No embeddings index found. Upload and process papers first."
            }
        
        # Search
        results = embedding_service.search(query, top_k=top_k, paper_ids=paper_ids)
        
        return {
            "status": "success",
            "query": query,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.post("/generate-report")
def generate_report(
    query: str,
    paper_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Generate a complete literature review report.
    Includes analysis, comparison, and research gaps.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if len(paper_ids) < 1:
        raise HTTPException(status_code=400, detail="At least 1 paper required")
    
    # Get papers
    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
    
    if len(papers) != len(paper_ids):
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
            query=query,
            papers=papers_data,
            comparison=comparison,
            research_gaps=gaps,
            retrieval_date=datetime.utcnow().strftime("%Y-%m-%d")
        )
        
        # Save research query
        research_query = ResearchQuery(query=query)
        db.add(research_query)
        db.commit()
        db.refresh(research_query)
        
        # Save report
        report = Report(
            query_id=research_query.id,
            title=f"Literature Review: {query}",
            report_content=report_markdown,
            paper_ids=json.dumps(paper_ids)
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
