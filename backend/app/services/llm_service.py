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
    
    def analyze_paper(self, chunks: List[Dict]) -> Dict:
        """
        Analyze a research paper using its text chunks.
        
        Args:
            chunks: List of text chunks with page numbers
        
        Returns:
            Structured analysis with evidence citations
        """
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
