"""
embedding_service.py
Handles text embeddings using sentence-transformers and FAISS for vector storage.
"""

import pickle
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from app.config import settings


class EmbeddingService:
    """Manages text embeddings and vector search using FAISS."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.model = None
        self.index = None
        self.dimension = settings.EMBEDDING_DIMENSION
        self.index_path = Path(settings.FAISS_INDEX_PATH)
        self.metadata_path = Path(settings.FAISS_METADATA_PATH)
        self.chunk_metadata = []  # Stores metadata for each vector
    
    def load_model(self):
        """Load the sentence transformer model, trying local cache first."""
        if self.model is None:
            try:
                # Fast path: use already cached model files without checking remote
                self.model = SentenceTransformer(self.model_name, local_files_only=True)
            except Exception:
                # Fallback to standard loading if not cached locally yet
                self.model = SentenceTransformer(self.model_name)
    
    def create_index(self):
        """Create a new FAISS index."""
        self.index = faiss.IndexFlatL2(self.dimension)
    
    def load_index(self):
        """Load existing FAISS index from disk."""
        if self.index_path.exists() and self.metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path, 'rb') as f:
                    self.chunk_metadata = pickle.load(f)
                return True
            except Exception as e:
                print(f"Warning: Failed to load FAISS index: {e}")
                return False
        return False
    
    def save_index(self):
        """Save FAISS index and metadata to disk."""
        if self.index is not None:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.index_path))
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.chunk_metadata, f)
    
    def add_embeddings(self, chunks: List[Dict]) -> List[int]:
        """
        Generate embeddings for chunks and add to index.
        
        Args:
            chunks: List of chunk dictionaries with text and metadata
        
        Returns:
            List of embedding references (indices in FAISS index)
        """
        self.load_model()
        
        if self.index is None:
            self.create_index()
        
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=False)
        
        # Add to FAISS index
        start_idx = self.index.ntotal
        self.index.add(embeddings.astype('float32'))
        
        # Store metadata
        embedding_refs = []
        for i, chunk in enumerate(chunks):
            ref = start_idx + i
            embedding_refs.append(ref)
            self.chunk_metadata.append({
                "ref": ref,
                "paper_id": chunk.get("paper_id"),
                "chunk_id": chunk.get("chunk_id"),
                "page_number": chunk.get("page_number"),
                "section": chunk.get("section"),
                "text": chunk["text"][:200]  # Store preview
            })
        
        return embedding_refs
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        paper_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Search for similar chunks.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            paper_ids: Optional list of paper IDs to filter by
        
        Returns:
            List of similar chunks with metadata and scores
        """
        self.load_model()
        
        if self.index is None or self.index.ntotal == 0:
            if not self.load_index() or self.index is None or self.index.ntotal == 0:
                return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], show_progress_bar=False)
        query_embedding = query_embedding.astype('float32')
        
        # Search: query more items if filtering by paper_ids to avoid dropping matches
        search_limit = min(max(top_k * 5, 20), self.index.ntotal) if paper_ids else min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, search_limit)
        
        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.chunk_metadata):
                metadata = self.chunk_metadata[idx].copy()
                metadata["score"] = float(1 / (1 + dist))  # Convert distance to similarity
                
                # Filter by paper IDs if specified
                if paper_ids is None or metadata.get("paper_id") in paper_ids:
                    results.append(metadata)
                    if len(results) >= top_k:
                        break
        
        return results

    def delete_by_paper_id(self, paper_id: int):
        """Remove all embeddings for a specific paper."""
        # Note: FAISS doesn't support deletion, so we rebuild the index
        if self.index is None:
            return
        
        # Filter out chunks for this paper
        filtered_metadata = [
            m for m in self.chunk_metadata 
            if m.get("paper_id") != paper_id
        ]
        
        if len(filtered_metadata) != len(self.chunk_metadata):
            # Rebuild index
            self.chunk_metadata = filtered_metadata
            self.create_index()
            
            # Re-add all remaining embeddings
            if self.chunk_metadata:
                texts = [m["text"] for m in self.chunk_metadata]
                embeddings = self.model.encode(texts, show_progress_bar=False)
                self.index.add(embeddings.astype('float32'))
            
            self.save_index()


# Global singleton instance
embedding_service = EmbeddingService()
