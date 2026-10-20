"""
citation_service.py
Semantic Citation & Agreement/Contradiction Graph.
Integrates Semantic Scholar and CrossRef APIs to fetch citations dynamically
and classify relationships between papers as SUPPORTS / CONTRADICTS / EXTENDS / UNRELATED.
"""

import json
import re
from typing import Dict, List, Optional
from app.config import settings


class CitationService:
    """
    Fetches citation data via Semantic Scholar / CrossRef APIs and builds
    a cross-paper consensus graph.
    """

    SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
    CROSSREF_BASE = "https://api.crossref.org/works"

    def __init__(self):
        self.mock_mode = (
            not settings.OPENAI_API_KEY
            or settings.OPENAI_API_KEY == "your_openai_api_key_here"
        )
        self.openai_client = None
        if not self.mock_mode:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception:
                pass

    def search_paper(self, title: str) -> Optional[Dict]:
        """
        Search Semantic Scholar for a paper by title.

        Returns:
            Paper dict with id, title, authors, year, abstract, citationCount,
            or None if not found / network unavailable.
        """
        try:
            import requests
            params = {
                "query": title,
                "fields": "paperId,title,authors,year,abstract,citationCount,references",
                "limit": 3,
            }
            resp = requests.get(
                f"{self.SEMANTIC_SCHOLAR_BASE}/paper/search",
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("data", [])
                if results:
                    return results[0]
        except Exception as e:
            print(f"[CitationService] Semantic Scholar search failed: {e}")
        return None

    def get_citations(self, semantic_paper_id: str) -> List[Dict]:
        """
        Fetch papers that cite the given Semantic Scholar paper.

        Returns:
            List of citation dicts.
        """
        try:
            import requests
            params = {
                "fields": "title,authors,year,abstract",
                "limit": 20,
            }
            resp = requests.get(
                f"{self.SEMANTIC_SCHOLAR_BASE}/paper/{semantic_paper_id}/citations",
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
        except Exception as e:
            print(f"[CitationService] Citation fetch failed: {e}")
        return []

    def classify_relationship(
        self,
        paper_a_text: str,
        paper_b_text: str,
        openai_client=None,
    ) -> str:
        """
        Classify the relationship between two papers as:
        SUPPORTS | CONTRADICTS | EXTENDS | UNRELATED

        Uses LLM when available, otherwise word-overlap heuristic.
        """
        if openai_client:
            try:
                prompt = (
                    f"Paper A findings:\n{paper_a_text[:500]}\n\n"
                    f"Paper B abstract:\n{paper_b_text[:500]}\n\n"
                    "Does Paper B SUPPORT, CONTRADICT, EXTEND, or is UNRELATED to Paper A? "
                    "Reply with exactly one word: SUPPORTS, CONTRADICTS, EXTENDS, or UNRELATED."
                )
                resp = openai_client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=10,
                )
                word = resp.choices[0].message.content.strip().upper()
                if word in ("SUPPORTS", "CONTRADICTS", "EXTENDS", "UNRELATED"):
                    return word
            except Exception as e:
                print(f"[CitationService] LLM classify failed: {e}")

        # Heuristic: word-overlap similarity
        def word_set(text: str):
            return set(re.findall(r"\b[a-z]{4,}\b", text.lower()))

        words_a = word_set(paper_a_text)
        words_b = word_set(paper_b_text)

        if not words_a or not words_b:
            return "UNRELATED"

        intersection = words_a & words_b
        union = words_a | words_b
        overlap = len(intersection) / len(union)

        contradiction_words = {
            "however", "contrary", "disagree", "contradict", "unlike",
            "opposed", "refute", "challenge", "inconsistent", "dispute",
        }
        has_contradiction = bool(intersection & contradiction_words)

        if has_contradiction and overlap > 0.15:
            return "CONTRADICTS"
        elif overlap > 0.30:
            return "SUPPORTS"
        elif overlap > 0.10:
            return "EXTENDS"
        else:
            return "UNRELATED"

    def build_citation_graph(
        self,
        paper_title: str,
        paper_abstract: str,
        openai_client=None,
    ) -> Dict:
        """
        Build a citation graph for a paper.

        Args:
            paper_title: The paper's title.
            paper_abstract: Abstract or summary of the paper's findings.
            openai_client: Optional OpenAI client for LLM classification.

        Returns:
            Dict with keys: paper, citations, graph_edges
        """
        found_paper = self.search_paper(paper_title)

        if found_paper is None:
            return {
                "paper": None,
                "citations": [],
                "graph_edges": [],
                "error": (
                    "Could not reach Semantic Scholar API. "
                    "Citation graph requires network access. "
                    "Please ensure the server has internet connectivity."
                ),
            }

        paper_id = found_paper.get("paperId", "")
        raw_citations = self.get_citations(paper_id) if paper_id else []

        citations = []
        graph_edges = []

        for item in raw_citations:
            cited = item.get("citingPaper") or item.get("citedPaper") or {}
            cited_title = cited.get("title", "")
            cited_abstract = cited.get("abstract", "") or ""
            cited_year = cited.get("year", "N/A")
            cited_authors = [a.get("name", "") for a in cited.get("authors", [])]

            if not cited_title:
                continue

            relationship = self.classify_relationship(
                paper_abstract or paper_title,
                cited_abstract or cited_title,
                openai_client,
            )

            citations.append({
                "title": cited_title,
                "year": cited_year,
                "authors": cited_authors[:3],
                "abstract": cited_abstract[:300] if cited_abstract else "",
                "relationship": relationship,
            })

            graph_edges.append({
                "source": paper_title,
                "target": cited_title,
                "relationship": relationship,
            })

        return {
            "paper": {
                "title": found_paper.get("title", paper_title),
                "year": found_paper.get("year"),
                "citation_count": found_paper.get("citationCount", 0),
                "semantic_scholar_id": paper_id,
            },
            "citations": citations,
            "graph_edges": graph_edges,
        }
