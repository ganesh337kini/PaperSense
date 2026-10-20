"""
llm_service.py
Handles LLM-powered paper analysis using OpenAI.
Generates structured analysis with evidence citations.
"""

import json
from typing import Dict, List, Optional
from openai import OpenAI
from app.config import settings


class LLMService:
    """Service for LLM-based paper analysis."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.OPENAI_MODEL
        self.mock_mode = not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here"
    
    def analyze_paper(self, chunks: List[Dict]) -> Dict:
        """
        Analyze a research paper using its text chunks.

        Args:
            chunks: List of text chunks with page numbers

        Returns:
            Structured analysis with evidence citations
        """
        if self.mock_mode:
            # Return mock response when no API key is configured
            return {
                "research_problem": "Mock research problem - configure OpenAI API key for real analysis",
                "research_objectives": "Mock objectives",
                "methodology": "Mock methodology",
                "dataset": "Mock dataset",
                "evaluation_metrics": "Mock metrics",
                "key_findings": "Mock findings",
                "main_contributions": "Mock contributions",
                "limitations": "Mock limitations",
                "future_work": "Mock future work",
                "evidence": {
                    "research_problem": {"text": "Mock evidence", "page": 1},
                    "methodology": {"text": "Mock evidence", "page": 2}
                }
            }

        if not self.client:
            raise Exception("OpenAI API key not configured")
        
        # Combine chunks into manageable sections
        full_text = "\n\n".join([
            f"[Page {c['page_number']}] {c['text']}" 
            for c in chunks
        ])
        
        # Truncate if too long (keep first 15000 chars for analysis)
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n\n[Text truncated due to length]"
        
        prompt = f"""
Analyze this research paper and provide a structured analysis. For each section, 
provide specific evidence with page references when available. If information is 
not available in the text, state "Not reported in the available text".

Paper text:
{full_text}

Return a JSON object with the following structure:
{{
    "research_problem": "What problem does this paper address?",
    "research_objectives": "What are the main objectives?",
    "methodology": "What methods/approaches are proposed?",
    "dataset": "What dataset or experimental environment is used?",
    "evaluation_metrics": "What metrics are used for evaluation?",
    "key_findings": "What are the main results?",
    "main_contributions": "What are the key contributions?",
    "limitations": "What limitations do the authors acknowledge?",
    "future_work": "What future work do the authors mention?",
    "evidence": {{
        "research_problem": {{"text": "quote", "page": number}},
        "methodology": {{"text": "quote", "page": number}},
        ...
    }}
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research assistant that analyzes academic papers. Always provide evidence with page references."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                # Extract JSON from response (in case there's extra text)
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    content = content[json_start:json_end]
                
                analysis = json.loads(content)
                return analysis
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "raw_analysis": content,
                    "error": "Failed to parse structured analysis"
                }
                
        except Exception as e:
            raise Exception(f"LLM analysis failed: {str(e)}")
    
    def compare_papers(self, papers: List[Dict]) -> Dict:
        """
        Compare multiple research papers.

        Args:
            papers: List of paper dictionaries with title, year, and analysis

        Returns:
            Comparison table and synthesis
        """
        if self.mock_mode:
            # Return mock response when no API key is configured
            return {
                "comparison_table": [
                    {
                        "title": papers[0].get("title", "Paper 1"),
                        "year": papers[0].get("year", "N/A"),
                        "research_problem": "Mock problem",
                        "methodology": "Mock methodology",
                        "dataset": "Mock dataset",
                        "evaluation_metrics": "Mock metrics",
                        "key_findings": "Mock findings",
                        "strengths": "Mock strengths",
                        "limitations": "Mock limitations",
                        "unresolved_questions": "Mock questions"
                    }
                ],
                "synthesis": "Mock synthesis - configure OpenAI API key for real comparison"
            }

        if not self.client:
            raise Exception("OpenAI API key not configured")
        
        # Build comparison context
        papers_text = "\n\n".join([
            f"Paper {i+1}: {p['title']} ({p.get('year', 'N/A')})\n"
            f"Problem: {p.get('analysis', {}).get('research_problem', 'N/A')}\n"
            f"Methodology: {p.get('analysis', {}).get('methodology', 'N/A')}\n"
            f"Findings: {p.get('analysis', {}).get('key_findings', 'N/A')}\n"
            f"Limitations: {p.get('analysis', {}).get('limitations', 'N/A')}"
            for i, p in enumerate(papers)
        ])
        
        prompt = f"""
Compare these research papers and provide:
1. A comparison table with: Title, Year, Research Problem, Methodology, Dataset, 
   Evaluation Metrics, Key Findings, Strengths, Limitations, Unresolved Questions
2. A synthesis explaining similarities, differences, conflicting findings, and implications

Papers:
{papers_text}

Return a JSON object with:
{{
    "comparison_table": [
        {{
            "title": "...",
            "year": "...",
            "research_problem": "...",
            "methodology": "...",
            "dataset": "...",
            "evaluation_metrics": "...",
            "key_findings": "...",
            "strengths": "...",
            "limitations": "...",
            "unresolved_questions": "..."
        }}
    ],
    "synthesis": "Detailed synthesis text"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research assistant that compares academic papers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2500
            )
            
            content = response.choices[0].message.content
            
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    content = content[json_start:json_end]
                
                comparison = json.loads(content)
                return comparison
            except json.JSONDecodeError:
                return {
                    "raw_comparison": content,
                    "error": "Failed to parse structured comparison"
                }
                
        except Exception as e:
            raise Exception(f"Paper comparison failed: {str(e)}")
    
    def detect_research_gaps(self, papers: List[Dict]) -> Dict:
        """
        Identify candidate research gaps from multiple papers.

        Args:
            papers: List of paper dictionaries with analysis

        Returns:
            Candidate research gaps with evidence
        """
        if self.mock_mode:
            # Return mock response when no API key is configured
            return {
                "research_gaps": [
                    {
                        "gap_statement": "Mock research gap",
                        "supporting_papers": [p.get("title", "Paper") for p in papers],
                        "evidence": "Mock evidence",
                        "why_it_matters": "Mock importance",
                        "research_question": "Mock research question",
                        "validation_approach": "Mock validation",
                        "confidence": "Low (mock mode)",
                        "rationale": "Mock rationale",
                        "alternative_explanations": "Mock alternatives"
                    }
                ]
            }

        if not self.client:
            raise Exception("OpenAI API key not configured")
        
        papers_text = "\n\n".join([
            f"Paper: {p['title']}\n"
            f"Limitations: {p.get('analysis', {}).get('limitations', 'N/A')}\n"
            f"Future Work: {p.get('analysis', {}).get('future_work', 'N/A')}"
            for p in papers
        ])
        
        prompt = f"""
Analyze these papers to identify candidate research gaps. For each gap, provide:
1. Concise gap statement
2. Supporting papers and page references
3. Evidence from each paper
4. Why the gap matters
5. Possible research question
6. Proposed validation approach
7. Confidence level (High/Medium/Low) with rationale
8. Alternative explanations

IMPORTANT: Label these as CANDIDATE research gaps, not proven discoveries. 
Do not claim no previous work exists without broad literature search support.

Papers:
{papers_text}

Return a JSON object with:
{{
    "research_gaps": [
        {{
            "gap_statement": "...",
            "supporting_papers": ["Paper 1", "Paper 2"],
            "evidence": "Specific evidence text",
            "why_it_matters": "...",
            "research_question": "...",
            "validation_approach": "...",
            "confidence": "High/Medium/Low",
            "rationale": "...",
            "alternative_explanations": "..."
        }}
    ]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research assistant that identifies candidate research gaps."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2500
            )
            
            content = response.choices[0].message.content
            
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    content = content[json_start:json_end]
                
                gaps = json.loads(content)
                return gaps
            except json.JSONDecodeError:
                return {
                    "raw_gaps": content,
                    "error": "Failed to parse structured gaps"
                }

        except Exception as e:
            raise Exception(f"Research gap detection failed: {str(e)}")

    def answer_question(self, question: str, chunks: List[Dict], paper_title: str = "") -> Dict:
        """
        Answer a specific question about a paper using its text chunks.

        Args:
            question: The user's question
            chunks: List of text chunks with page numbers
            paper_title: Title of the paper

        Returns:
            Answer with evidence citations
        """
        if self.mock_mode or not self.client:
            return self._generate_grounded_answer(question, chunks, paper_title)

        # Select most relevant chunks (top 8 max to stay within token limits)
        selected_chunks = chunks[:8]
        full_text = "\n\n".join([
            f"[Page {c.get('page_number', 'N/A')}] {c.get('text', '')}"
            for c in selected_chunks
        ])

        if len(full_text) > 12000:
            full_text = full_text[:12000] + "\n\n[Text truncated due to length]"

        prompt = f"""
You are analyzing a research paper titled: {paper_title}

Relevant paper passages:
{full_text}

Question: {question}

Provide a clear, accurate answer based ONLY on the paper text above. If the answer is not in the text, state that clearly.

Return a JSON object with the following structure:
{{
    "answer": "Your detailed answer to the question",
    "evidence": [
        {{
            "text": "Direct quote from the paper supporting your answer",
            "page": page_number,
            "relevance": "Brief explanation of how this evidence supports the answer"
        }}
    ],
    "confidence": "High/Medium/Low",
    "reasoning": "Brief explanation of your reasoning process"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research assistant that answers questions about academic papers. Always provide evidence with page references."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )

            content = response.choices[0].message.content

            # Parse JSON response
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    content = content[json_start:json_end]

                answer = json.loads(content)
                return answer
            except json.JSONDecodeError:
                return {
                    "answer": content,
                    "evidence": [],
                    "confidence": "Medium",
                    "reasoning": "Raw answer generated by model"
                }

        except Exception as e:
            # Fall back to grounded answer if OpenAI fails
            grounded = self._generate_grounded_answer(question, chunks, paper_title)
            grounded["warning"] = f"AI completion failed ({str(e)}), showing extracted paper passages."
            return grounded

    def _generate_grounded_answer(self, question: str, chunks: List[Dict], paper_title: str = "") -> Dict:
        """
        Produce a grounded answer with real evidence citations directly from paper chunks
        when running offline or without an OpenAI API key.
        """
        if not chunks:
            return {
                "answer": f"No relevant content found in the paper to answer: '{question}'.",
                "evidence": [],
                "confidence": "Low",
                "reasoning": "No text chunks available for retrieval."
            }

        title_prefix = f"In \"{paper_title}\", " if paper_title else ""
        top_chunk = chunks[0]
        top_text = top_chunk.get("text", "").strip()
        top_page = top_chunk.get("page_number", 1)
        top_section = top_chunk.get("section") or "Relevant Section"

        # Build evidence items from top matching chunks
        evidence_list = []
        for c in chunks[:3]:
            text = c.get("text", "").strip()
            if text:
                quote = text[:300] + ("..." if len(text) > 300 else "")
                evidence_list.append({
                    "text": quote,
                    "page": c.get("page_number", 1),
                    "relevance": f"Found on page {c.get('page_number', 1)} addressing the query"
                })

        # Synthesize a clean, readable answer from the top text
        excerpt = top_text[:450] + ("..." if len(top_text) > 450 else "")
        answer_text = (
            f"{title_prefix}the most relevant section discussing this was found on Page {top_page} "
            f"({top_section}):\n\n\"{excerpt}\""
        )

        return {
            "answer": answer_text,
            "evidence": evidence_list,
            "confidence": "High (Extracted from paper)",
            "reasoning": f"Identified {len(chunks)} relevant passage(s) directly from the paper using semantic vector search."
        }

