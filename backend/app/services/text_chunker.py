"""
text_chunker.py
Splits extracted text into overlapping chunks with metadata.
Preserves page numbers and section information.
"""

from typing import List, Dict, Tuple
import re


class TextChunker:
    """Splits text into overlapping chunks for semantic search."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        min_chunk_size: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_pages(
        self,
        pages_text: List[Tuple[int, str]]
    ) -> List[Dict]:
        """
        Chunk text from multiple pages with overlap.
        
        Args:
            pages_text: List of (page_number, text) tuples
        
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        chunk_index = 0
        
        for page_num, text in pages_text:
            # Split text into sentences first for better boundaries
            sentences = self._split_into_sentences(text)
            
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_length = len(sentence)
                
                # If adding this sentence would exceed chunk size
                if current_length + sentence_length > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = " ".join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append({
                            "text": chunk_text,
                            "page_number": page_num,
                            "chunk_index": chunk_index,
                            "section": self._detect_section(chunk_text)
                        })
                        chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_chunks = self._get_overlap_chunks(current_chunk)
                    current_chunk = overlap_chunks
                    current_length = sum(len(c) for c in current_chunk)
                
                current_chunk.append(sentence)
                current_length += sentence_length
            
            # Don't forget the last chunk on the page
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append({
                        "text": chunk_text,
                        "page_number": page_num,
                        "chunk_index": chunk_index,
                        "section": self._detect_section(chunk_text)
                    })
                    chunk_index += 1
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        # Simple sentence splitting - can be improved
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_chunks(self, chunks: List[str]) -> List[str]:
        """Get overlapping chunks from the end of current chunks."""
        overlap_text = " ".join(chunks)
        words = overlap_text.split()
        
        # Calculate how many words to keep for overlap
        overlap_chars = self.chunk_overlap
        overlap_words = []
        char_count = 0
        
        for word in reversed(words):
            if char_count + len(word) > overlap_chars:
                break
            overlap_words.insert(0, word)
            char_count += len(word) + 1  # +1 for space
        
        return [" ".join(overlap_words)] if overlap_words else []
    
    def _detect_section(self, text: str) -> str:
        """Detect section heading from chunk text."""
        text_lower = text.lower()
        
        section_keywords = {
            "abstract": ["abstract"],
            "introduction": ["introduction", "1.", "1.1"],
            "related work": ["related work", "background", "literature review"],
            "methodology": ["methodology", "methods", "approach", "method"],
            "experiments": ["experiment", "evaluation", "setup"],
            "results": ["results", "findings"],
            "discussion": ["discussion"],
            "conclusion": ["conclusion", "conclusions", "future work"],
            "references": ["references", "bibliography"]
        }
        
        for section, keywords in section_keywords.items():
            for keyword in keywords:
                if keyword in text_lower[:200]:  # Check beginning of chunk
                    return section
        
        return None
