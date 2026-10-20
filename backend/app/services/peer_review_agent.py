"""
peer_review_agent.py
Adversarial Peer Review Agent — automatically stress-tests uploaded papers
for scientific rigor. Generates audit reports covering baseline fairness,
missing ablation studies, hidden assumptions, and data leakage.
"""

import json
import re
from typing import List, Dict, Optional
from app.config import settings


class PeerReviewAgent:
    """
    Agentic module that critically evaluates a research paper and returns
    a structured review report with severity-tagged findings.
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
                print(f"[PeerReviewAgent] Could not init OpenAI client: {e}")
                self.mock_mode = True

    def run_peer_review(self, paper_title: str, chunks: List[Dict]) -> Dict:
        """
        Run the full peer review pipeline on a paper.

        Args:
            paper_title: Title of the paper.
            chunks: List of text chunks with page_number and section fields.

        Returns:
            Dict with findings, overall_score, and summary.
        """
        if self.mock_mode or self.client is None:
            return self._heuristic_review(paper_title, chunks)
        return self._llm_review(paper_title, chunks)

    def _heuristic_review(self, paper_title: str, chunks: List[Dict]) -> Dict:
        """
        Heuristic peer review based on keyword scanning across chunks.
        Works offline without any API key.
        """
        full_text = " ".join(c.get("text", "") for c in chunks).lower()
        findings = []
        score = 100  # Start at 100 and deduct for issues

        # --- Baseline Fairness ---
        baseline_kws = ["baseline", "compared to", "state-of-the-art", "sota",
                        "outperforms", "benchmark", "versus", "vs."]
        has_baseline = any(kw in full_text for kw in baseline_kws)
        if not has_baseline:
            findings.append({
                "category": "Baseline Fairness",
                "severity": "critical",
                "description": (
                    "No explicit baseline comparison or state-of-the-art benchmark detected. "
                    "Papers should compare against established baselines to validate improvements."
                ),
                "evidence_text": "No 'baseline', 'SOTA', or comparison language found in the paper.",
                "page": 1,
            })
            score -= 20
        else:
            findings.append({
                "category": "Baseline Fairness",
                "severity": "info",
                "description": "Baseline or comparative evaluation language detected.",
                "evidence_text": self._find_context(full_text, baseline_kws, chunks),
                "page": self._find_page(chunks, baseline_kws),
            })

        # --- Ablation Studies ---
        ablation_kws = ["ablation", "ablat", "component analysis", "module analysis",
                        "without", "w/o", "removing"]
        has_ablation = any(kw in full_text for kw in ablation_kws)
        if not has_ablation:
            findings.append({
                "category": "Ablation Studies",
                "severity": "warning",
                "description": (
                    "No ablation study detected. Ablation studies are important for understanding "
                    "which components contribute to the reported performance gains."
                ),
                "evidence_text": "No ablation-related language found.",
                "page": 1,
            })
            score -= 15
        else:
            findings.append({
                "category": "Ablation Studies",
                "severity": "info",
                "description": "Ablation or component analysis appears to be present.",
                "evidence_text": self._find_context(full_text, ablation_kws, chunks),
                "page": self._find_page(chunks, ablation_kws),
            })

        # --- Hidden Assumptions ---
        assumption_kws = ["assume", "assumption", "we assume", "assuming", "presume",
                          "it is assumed", "given that"]
        assumption_evidence = []
        for chunk in chunks:
            text = chunk.get("text", "").lower()
            for kw in assumption_kws:
                if kw in text:
                    idx = text.find(kw)
                    snippet = chunk.get("text", "")[max(0, idx - 20):idx + 100]
                    assumption_evidence.append({
                        "text": snippet,
                        "page": chunk.get("page_number", 1)
                    })
                    break

        if assumption_evidence:
            findings.append({
                "category": "Hidden Assumptions",
                "severity": "warning",
                "description": (
                    f"Found {len(assumption_evidence)} potential hidden assumption(s). "
                    "These should be explicitly justified or empirically validated."
                ),
                "evidence_text": "; ".join(
                    f"[Page {e['page']}] \"{e['text'].strip()}\"" for e in assumption_evidence[:3]
                ),
                "page": assumption_evidence[0]["page"],
            })
            score -= 10
        else:
            findings.append({
                "category": "Hidden Assumptions",
                "severity": "info",
                "description": "No explicit hidden assumptions flagged.",
                "evidence_text": "",
                "page": 1,
            })

        # --- Data Leakage ---
        leakage_kws = ["leakage", "contamination", "data leakage", "test set",
                       "validation set leakage", "train-test overlap"]
        has_leakage_concern = any(kw in full_text for kw in leakage_kws)
        train_test_pattern = bool(re.search(r"train\w*\s.{0,50}test\w*", full_text))

        if has_leakage_concern:
            findings.append({
                "category": "Data Leakage",
                "severity": "critical",
                "description": (
                    "Data leakage or contamination language detected. "
                    "Verify that training data does not overlap with test/validation sets."
                ),
                "evidence_text": self._find_context(full_text, leakage_kws, chunks),
                "page": self._find_page(chunks, leakage_kws),
            })
            score -= 25
        elif train_test_pattern:
            findings.append({
                "category": "Data Leakage",
                "severity": "warning",
                "description": (
                    "Training and test set references found in close proximity. "
                    "Ensure proper data splits are maintained and described clearly."
                ),
                "evidence_text": "Train/test co-occurrence pattern detected.",
                "page": 1,
            })
            score -= 5
        else:
            findings.append({
                "category": "Data Leakage",
                "severity": "info",
                "description": "No obvious data leakage indicators found.",
                "evidence_text": "",
                "page": 1,
            })

        # --- Statistical Significance ---
        stat_kws = ["p-value", "p value", "statistical", "significance", "confidence interval",
                    "standard deviation", "error bar", "95%"]
        has_stats = any(kw in full_text for kw in stat_kws)
        if not has_stats:
            findings.append({
                "category": "Statistical Rigor",
                "severity": "warning",
                "description": (
                    "No statistical significance tests or confidence intervals detected. "
                    "Results should include p-values, error bars, or confidence intervals."
                ),
                "evidence_text": "No statistical significance language found.",
                "page": 1,
            })
            score -= 10
        else:
            findings.append({
                "category": "Statistical Rigor",
                "severity": "info",
                "description": "Statistical evaluation language detected.",
                "evidence_text": self._find_context(full_text, stat_kws, chunks),
                "page": self._find_page(chunks, stat_kws),
            })

        score = max(0, score)

        if score >= 80:
            grade = "Strong"
        elif score >= 60:
            grade = "Acceptable"
        elif score >= 40:
            grade = "Needs Improvement"
        else:
            grade = "Significant Issues"

        critical_count = sum(1 for f in findings if f["severity"] == "critical")
        warning_count = sum(1 for f in findings if f["severity"] == "warning")

        return {
            "findings": findings,
            "overall_score": score,
            "grade": grade,
            "summary": (
                f"Heuristic peer review of \"{paper_title}\" complete. "
                f"Score: {score}/100 ({grade}). "
                f"{critical_count} critical issue(s), {warning_count} warning(s) detected. "
                "Configure an OpenAI API key for LLM-powered in-depth analysis."
            ),
            "mode": "heuristic",
        }

    def _llm_review(self, paper_title: str, chunks: List[Dict]) -> Dict:
        """
        LLM-powered peer review using OpenAI.
        Falls back to heuristic on failure.
        """
        selected = chunks[:10]
        context = "\n\n".join(
            f"[Page {c.get('page_number', '?')}] {c.get('text', '')[:400]}"
            for c in selected
        )

        prompt = f"""You are a critical peer reviewer for a top-tier machine learning conference (NeurIPS / ICML / ICLR level).

Paper title: "{paper_title}"

Paper excerpts:
{context}

Perform a rigorous peer review and return a JSON object with this exact structure:
{{
  "findings": [
    {{
      "category": "Baseline Fairness|Ablation Studies|Hidden Assumptions|Data Leakage|Statistical Rigor|Reproducibility|Novelty",
      "severity": "critical|warning|info",
      "description": "Detailed description of the issue or positive finding",
      "evidence_text": "Specific quote or reference from the paper",
      "page": 1
    }}
  ],
  "overall_score": 75,
  "grade": "Strong|Acceptable|Needs Improvement|Significant Issues",
  "summary": "Overall assessment paragraph"
}}

Check for: missing baselines, no ablation studies, hidden assumptions, data leakage risks, lack of statistical tests, reproducibility issues, and overblown claims."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert peer reviewer. Always return valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            content = response.choices[0].message.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
                result["mode"] = "llm"
                return result
        except Exception as e:
            print(f"[PeerReviewAgent] LLM review failed: {e}, falling back to heuristic")

        return self._heuristic_review(paper_title, chunks)

    def _find_context(self, full_text_lower: str, keywords: List[str], chunks: List[Dict]) -> str:
        """Find the first chunk containing any keyword and return a snippet."""
        for chunk in chunks:
            text = chunk.get("text", "")
            for kw in keywords:
                if kw in text.lower():
                    idx = text.lower().find(kw)
                    return f"[Page {chunk.get('page_number', '?')}] \"...{text[max(0, idx - 20):idx + 100]}...\""
        return ""

    def _find_page(self, chunks: List[Dict], keywords: List[str]) -> int:
        """Find page number of first chunk containing any keyword."""
        for chunk in chunks:
            text = chunk.get("text", "").lower()
            if any(kw in text for kw in keywords):
                return chunk.get("page_number", 1)
        return 1
