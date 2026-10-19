"""
pdf_extractor.py
Handles PDF text extraction using PyMuPDF.
Extracts text with page numbers and detects image-only PDFs.
"""

import fitz  # PyMuPDF
from typing import List, Tuple, Optional
from pathlib import Path


class PDFExtractor:
    """Extracts text from PDF files with page tracking."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.doc = None
    
    def extract_text(self) -> Tuple[List[Tuple[int, str]], int]:
        """
        Extract text from PDF with page numbers.
        
        Returns:
            Tuple of (list of (page_number, text) tuples, total_pages)
        
        Raises:
            Exception: If PDF is encrypted, corrupt, or empty
        """
        try:
            self.doc = fitz.open(self.file_path)
            
            if self.doc.is_encrypted:
                raise Exception("PDF is encrypted and cannot be processed")
            
            total_pages = len(self.doc)
            if total_pages == 0:
                raise Exception("PDF has no pages")
            
            pages_text = []
            total_chars = 0
            
            for page_num in range(total_pages):
                page = self.doc[page_num]
                text = page.get_text()
                
                if text.strip():
                    pages_text.append((page_num + 1, text))
                    total_chars += len(text)
            
            # Check if PDF is image-only (very little text extracted)
            if total_chars < 100 and total_pages > 0:
                self.doc.close()
                raise Exception(
                    "PDF appears to be image-only or scanned. "
                    "OCR is required but not currently supported."
                )
            
            if not pages_text:
                self.doc.close()
                raise Exception("No extractable text found in PDF")
            
            return pages_text, total_pages
            
        except Exception as e:
            if self.doc:
                self.doc.close()
            raise Exception(f"PDF extraction failed: {str(e)}")
        finally:
            if self.doc:
                self.doc.close()
    
    def get_metadata(self) -> dict:
        """Extract basic PDF metadata."""
        try:
            self.doc = fitz.open(self.file_path)
            metadata = {
                "title": self.doc.metadata.get("title", ""),
                "author": self.doc.metadata.get("author", ""),
                "subject": self.doc.metadata.get("subject", ""),
                "creator": self.doc.metadata.get("creator", ""),
                "producer": self.doc.metadata.get("producer", ""),
            }
            return metadata
        except Exception:
            return {}
        finally:
            if self.doc:
                self.doc.close()
