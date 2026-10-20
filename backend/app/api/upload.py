"""
upload.py
API endpoints for PDF upload and processing.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid
from typing import List

from app.database import get_db
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.pdf_extractor import PDFExtractor
from app.services.text_chunker import TextChunker
from app.services.embedding_service import embedding_service
from app.config import settings

router = APIRouter()
chunker = TextChunker()


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF research paper for processing.
    Validates file type, extracts text, chunks it, and stores in database.
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Check file size
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )
    
    # Reset file pointer
    await file.seek(0)
    
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(exist_ok=True)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.pdf"
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create paper record
    paper = Paper(
        title=file.filename.replace('.pdf', ''),
        source="upload",
        file_name=file.filename,
        file_path=str(file_path),
        processing_status="queued"
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    
    # Process PDF (extract text, chunk, embed)
    try:
        paper.processing_status = "processing"
        db.commit()
        
        # Extract text
        extractor = PDFExtractor(str(file_path))
        pages_text, total_pages = extractor.extract_text()
        
        # Get metadata from PDF
        pdf_metadata = extractor.get_metadata()
        if pdf_metadata.get("title"):
            paper.title = pdf_metadata["title"][:500]
        if pdf_metadata.get("author"):
            paper.authors = pdf_metadata["author"]
        
        paper.total_pages = total_pages
        
        # Chunk text
        chunks_data = chunker.chunk_pages(pages_text)
        
        # Save chunks to database
        for chunk_data in chunks_data:
            chunk = PaperChunk(
                paper_id=paper.id,
                text=chunk_data["text"],
                page_number=chunk_data["page_number"],
                chunk_index=chunk_data["chunk_index"],
                section=chunk_data["section"]
            )
            db.add(chunk)
        
        db.commit()
        db.refresh(paper)
        
        # --- Pillar 1: Layout-aware bbox enrichment ---
        try:
            from app.services.layout_parser import LayoutParser
            layout_chunks = LayoutParser().extract_with_layout(str(file_path))
            # Build a lookup: page_number -> list of layout blocks
            page_to_blocks: dict = {}
            for lb in layout_chunks:
                pg = lb.get("page_number", 1)
                page_to_blocks.setdefault(pg, []).append(lb)

            saved_chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == paper.id).all()
            for chunk in saved_chunks:
                pg = chunk.page_number or 1
                blocks = page_to_blocks.get(pg, [])
                idx = chunk.chunk_index or 0
                if blocks:
                    block = blocks[idx % len(blocks)]
                    chunk.bbox_x0 = block.get("bbox_x0")
                    chunk.bbox_y0 = block.get("bbox_y0")
                    chunk.bbox_x1 = block.get("bbox_x1")
                    chunk.bbox_y1 = block.get("bbox_y1")
                    chunk.block_type = block.get("block_type", "text")
            db.commit()
        except Exception:
            pass  # Layout enrichment is best-effort
        
        # Generate embeddings
        embedding_service.load_index() or embedding_service.create_index()
        
        # Prepare chunks for embedding
        chunks_for_embedding = []
        for chunk_data in chunks_data:
            chunks_for_embedding.append({
                "text": chunk_data["text"],
                "paper_id": paper.id,
                "chunk_id": chunk_data["chunk_index"],
                "page_number": chunk_data["page_number"],
                "section": chunk_data["section"]
            })
        
        embedding_refs = embedding_service.add_embeddings(chunks_for_embedding)
        
        # Update chunks with embedding references
        chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == paper.id).all()
        for chunk, ref in zip(chunks, embedding_refs):
            chunk.embedding_reference = str(ref)
        
        # Save index
        embedding_service.save_index()
        
        paper.processing_status = "completed"
        db.commit()
        
        return {
            "status": "success",
            "paper_id": paper.id,
            "title": paper.title,
            "total_pages": total_pages,
            "chunks_created": len(chunks_data),
            "message": "PDF uploaded and processed successfully"
        }
        
    except Exception as e:
        paper.processing_status = "failed"
        paper.processing_error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")


@router.get("/papers")
def list_papers(db: Session = Depends(get_db)):
    """List all uploaded papers with their processing status."""
    papers = db.query(Paper).filter(Paper.source == "upload").order_by(Paper.created_at.desc()).all()
    
    return {
        "status": "success",
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "file_name": p.file_name,
                "processing_status": p.processing_status,
                "total_pages": p.total_pages,
                "created_at": p.created_at.isoformat(),
                "processing_error": p.processing_error
            }
            for p in papers
        ]
    }


@router.get("/papers/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """Get details of a specific paper including its chunks."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == paper_id).order_by(PaperChunk.chunk_index).all()
    
    return {
        "status": "success",
        "paper": {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "year": paper.year,
            "doi": paper.doi,
            "source": paper.source,
            "processing_status": paper.processing_status,
            "total_pages": paper.total_pages,
            "analysis": paper.analysis,
            "created_at": paper.created_at.isoformat()
        },
        "chunks": [
            {
                "id": c.id,
                "text": c.text,
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
                "section": c.section
            }
            for c in chunks
        ]
    }


@router.delete("/papers/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """Delete a paper and its chunks."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Delete file if exists
    if paper.file_path:
        file_path = Path(paper.file_path)
        if file_path.exists():
            file_path.unlink()
    
    # Remove embeddings
    embedding_service.load_index()
    embedding_service.delete_by_paper_id(paper_id)
    embedding_service.save_index()
    
    # Delete from database (cascade will delete chunks)
    db.delete(paper)
    db.commit()
    
    return {"status": "success", "message": "Paper deleted successfully"}



@router.get("/papers/{paper_id}/pdf")
def serve_paper_pdf(paper_id: int, db: Session = Depends(get_db)):
    """Serve the raw PDF file for a paper."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.file_path or not Path(paper.file_path).exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(
        paper.file_path,
        media_type="application/pdf",
        filename=paper.file_name or f"paper_{paper_id}.pdf"
    )
