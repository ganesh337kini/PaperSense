"""
hypothesis_agent.py
Hypothesis Generation & What-If Experiment Simulator.
Creates an agentic brainstorming sandbox where researchers can query
modified experimental conditions grounded in the paper's own text.
"""

import json
import re
from typing import List, Dict
from app.config import settings


class HypothesisAgent:
    """
    Generates research hypotheses and simulates 'what-if' experimental
    scenarios based on a paper's content.
    """

    def __init__(self):
        self.mock_mode = (
            not settings.OPENAI_API_KEY
            or settings.OPENAI_API_KEY == "your_openai_api_key_here"
        )
        self.client = None
        if not self.mock_mode:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                print(f"[HypothesisAgent] Could not init OpenAI client: {e}")
                self.mock_mode = True

    def generate_hypothesis(
        self,
        paper_title: str,
        chunks: List[Dict],
        what_if_question: str,
    ) -> Dict:
        """
        Generate a hypothesis and predicted outcomes for a what-if question.

        Args:
            paper_title: Title of the paper being analyzed.
            chunks: Text chunks from the paper.
            what_if_question: The researcher's what-if scenario question.

        Returns:
            Dict with hypothesis, predicted_outcomes, suggested_experiments,
            relevant_sections, confidence, limitations.
        """
        if self.mock_mode or self.client is None:
            return self._heuristic_hypothesis(paper_title, chunks, what_if_question)
        return self._llm_hypothesis(paper_title, chunks, what_if_question)

    def _rank_chunks_by_relevance(
        self, chunks: List[Dict], question: str, top_k: int = 6
    ) -> List[Dict]:
        """
        Simple keyword-overlap ranking to find most relevant chunks.
        """
        question_words = set(re.findall(r"\b[a-z]{3,}\b", question.lower()))

        scored = []
        for chunk in chunks:
            text = chunk.get("text", "").lower()
            chunk_words = set(re.findall(r"\b[a-z]{3,}\b", text))
            overlap = len(question_words & chunk_words)
            scored.append((overlap, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def _heuristic_hypothesis(
        self,
        paper_title: str,
        chunks: List[Dict],
        question: str,
    ) -> Dict:
        """
        Generate a heuristic hypothesis from keyword-matched paper excerpts.
        Works offline without any API key.
        """
        top_chunks = self._rank_chunks_by_relevance(chunks, question)

        relevant_sections = []
        for c in top_chunks[:3]:
            text = c.get("text", "").strip()
            if text:
                relevant_sections.append({
                    "text": text[:300] + ("..." if len(text) > 300 else ""),
                    "page": c.get("page_number", 1),
                    "section": c.get("section", ""),
                })

        top_text = top_chunks[0].get("text", "") if top_chunks else ""
        excerpt = top_text[:400] + ("..." if len(top_text) > 400 else "")
        top_page = top_chunks[0].get("page_number", 1) if top_chunks else 1

        hypothesis_text = (
            f"Based on \"{paper_title}\", regarding your scenario: \"{question}\"\n\n"
            f"The paper's most relevant discussion (Page {top_page}):\n"
            f"\"{excerpt}\"\n\n"
            f"A plausible hypothesis is that modifying the experimental conditions as described "
            f"would likely affect the core findings proportionally to how central those conditions "
            f"are to the methodology. The paper's existing framework would need to be re-evaluated "
            f"under the new scenario."
        )

        return {
            "hypothesis": hypothesis_text,
            "predicted_outcomes": [
                "Performance metrics may shift depending on the similarity between the new and original conditions.",
                "The proposed modifications could expose edge cases not covered in the original experimental setup.",
                "Generalizability of the findings may improve or degrade based on dataset/domain shift.",
            ],
            "suggested_experiments": [
                f"Re-run the core experiment described in the paper with the modified conditions from: \"{question}\"",
                "Conduct an ablation study isolating the specific component being changed.",
                "Compare results against the original baseline reported in the paper.",
                "Validate on an additional held-out dataset to test robustness.",
            ],
            "relevant_sections": relevant_sections,
            "confidence": "Medium (heuristic mode — results are keyword-matched excerpts)",
            "limitations": (
                "This is a heuristic estimate based on keyword retrieval. "
                "For AI-powered hypothesis generation with causal reasoning, "
                "configure an OpenAI API key in backend/.env."
            ),
            "mode": "heuristic",
        }

    def _llm_hypothesis(
        self,
        paper_title: str,
        chunks: List[Dict],
        question: str,
    ) -> Dict:
        """
        LLM-powered hypothesis generation. Falls back to heuristic on error.
        """
        top_chunks = self._rank_chunks_by_relevance(chunks, question)
        context = "\n\n".join(
            f"[Page {c.get('page_number', '?')}, {c.get('section', '')}]\n{c.get('text', '')[:400]}"
            for c in top_chunks
        )

        prompt = f"""You are a research scientist brainstorming about a paper.

Paper: "{paper_title}"

Relevant sections from the paper:
{context}

Researcher's what-if question: "{question}"

Generate a rigorous scientific hypothesis and experimental plan. Return a JSON object:
{{
  "hypothesis": "A clear, testable hypothesis addressing the what-if scenario, grounded in the paper",
  "predicted_outcomes": ["outcome 1", "outcome 2", "outcome 3"],
  "suggested_experiments": ["experiment 1", "experiment 2", "experiment 3"],
  "relevant_sections": [
    {{"text": "quote from paper", "page": 1, "section": "section name"}}
  ],
  "confidence": "High|Medium|Low with brief reason",
  "limitations": "What assumptions or limitations apply to this hypothesis"
}}

Base your hypothesis ONLY on evidence from the provided paper sections."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a research scientist that generates grounded, testable hypotheses "
                            "from academic papers. Always return valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1500,
            )
            content = response.choices[0].message.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
                result["mode"] = "llm"
                return result
        except Exception as e:
            print(f"[HypothesisAgent] LLM hypothesis failed: {e}, falling back to heuristic")

        return self._heuristic_hypothesis(paper_title, chunks, question)
