"""
report_service.py
Generates structured literature review reports in Markdown format.
"""

import json
from typing import Dict, List
from datetime import datetime


class ReportService:
    """Service for generating literature review reports."""
    
    def generate_report(
        self,
        query: str,
        papers: List[Dict],
        comparison: Dict,
        research_gaps: Dict,
        retrieval_date: str = None
    ) -> str:
        """
        Generate a complete literature review report in Markdown.
        
        Args:
            query: Research question/topic
            papers: List of papers with metadata and analysis
            comparison: Paper comparison results
            research_gaps: Research gap analysis results
            retrieval_date: When papers were retrieved
        
        Returns:
            Markdown-formatted report
        """
        if retrieval_date is None:
            retrieval_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        report_lines = []
        
        # Title and metadata
        report_lines.append(f"# Literature Review: {query}\n")
        report_lines.append(f"**Retrieval Date:** {retrieval_date}\n")
        report_lines.append(f"**Number of Papers:** {len(papers)}\n")
        report_lines.append("---\n")
        
        # Executive Summary
        report_lines.append("## Executive Summary\n")
        report_lines.append(self._generate_executive_summary(papers, comparison, research_gaps))
        report_lines.append("\n")
        
        # Search Strategy
        report_lines.append("## Search Strategy\n")
        report_lines.append(f"- **Query:** {query}\n")
        report_lines.append(f"- **Retrieval Date:** {retrieval_date}\n")
        report_lines.append(f"- **Selection Criteria:** Papers analyzed based on relevance to research question\n")
        report_lines.append("\n")
        
        # Included Papers
        report_lines.append("## Included Papers\n")
        for i, paper in enumerate(papers, 1):
            report_lines.append(f"{i}. **{paper['title']}** ({paper.get('year', 'N/A')})\n")
            if paper.get('doi'):
                report_lines.append(f"   - DOI: {paper['doi']}\n")
            if paper.get('url'):
                report_lines.append(f"   - URL: {paper['url']}\n")
        report_lines.append("\n")
        
        # Paper-by-Paper Analysis
        report_lines.append("## Paper-by-Paper Analysis\n")
        for paper in papers:
            report_lines.append(f"### {paper['title']}\n\n")
            analysis = paper.get('analysis', {})
            
            if analysis.get('research_problem'):
                report_lines.append(f"**Research Problem:** {analysis['research_problem']}\n\n")
            if analysis.get('methodology'):
                report_lines.append(f"**Methodology:** {analysis['methodology']}\n\n")
            if analysis.get('key_findings'):
                report_lines.append(f"**Key Findings:** {analysis['key_findings']}\n\n")
            if analysis.get('limitations'):
                report_lines.append(f"**Limitations:** {analysis['limitations']}\n\n")
            if analysis.get('future_work'):
                report_lines.append(f"**Future Work:** {analysis['future_work']}\n\n")
            report_lines.append("---\n")
        
        # Comparative Review
        report_lines.append("## Comparative Literature Review\n")
        if comparison.get('synthesis'):
            report_lines.append(comparison['synthesis'])
            report_lines.append("\n\n")
        
        if comparison.get('comparison_table'):
            report_lines.append("### Comparison Table\n")
            report_lines.append(self._generate_comparison_table(comparison['comparison_table']))
            report_lines.append("\n")
        
        # Research Gaps
        report_lines.append("## Research Gaps and Future Directions\n")
        gaps = research_gaps.get('research_gaps', [])
        if gaps:
            for i, gap in enumerate(gaps, 1):
                report_lines.append(f"### Gap {i}: {gap.get('gap_statement', 'N/A')}\n\n")
                report_lines.append(f"**Supporting Papers:** {', '.join(gap.get('supporting_papers', []))}\n\n")
                report_lines.append(f"**Evidence:** {gap.get('evidence', 'N/A')}\n\n")
                report_lines.append(f"**Why It Matters:** {gap.get('why_it_matters', 'N/A')}\n\n")
                report_lines.append(f"**Research Question:** {gap.get('research_question', 'N/A')}\n\n")
                report_lines.append(f"**Validation Approach:** {gap.get('validation_approach', 'N/A')}\n\n")
                report_lines.append(f"**Confidence:** {gap.get('confidence', 'N/A')} - {gap.get('rationale', 'N/A')}\n\n")
                if gap.get('alternative_explanations'):
                    report_lines.append(f"**Alternative Explanations:** {gap.get('alternative_explanations')}\n\n")
                report_lines.append("---\n")
        else:
            report_lines.append("No specific research gaps identified in the analyzed papers.\n\n")
        
        # Proposed Future Research
        report_lines.append("## Proposed Future Research Directions\n")
        report_lines.append(self._generate_future_research(gaps))
        report_lines.append("\n")
        
        # References
        report_lines.append("## References\n")
        for paper in papers:
            if paper.get('doi'):
                report_lines.append(f"- {paper['title']}. DOI: {paper['doi']}\n")
            elif paper.get('url'):
                report_lines.append(f"- {paper['title']}. Available at: {paper['url']}\n")
            else:
                report_lines.append(f"- {paper['title']}\n")
        
        # Limitations
        report_lines.append("\n## Analysis Limitations\n")
        report_lines.append("- Analysis based on available text content from uploaded papers\n")
        report_lines.append("- May not capture all relevant literature in the field\n")
        report_lines.append("- Research gaps are candidate suggestions requiring further validation\n")
        report_lines.append("- AI-generated analysis should be verified against original sources\n")
        
        return "".join(report_lines)
    
    def _generate_executive_summary(self, papers, comparison, research_gaps) -> str:
        """Generate executive summary section."""
        summary = f"This literature review analyzes {len(papers)} research papers related to the query. "
        
        if comparison.get('synthesis'):
            summary += "The papers show both complementary approaches and some divergent findings. "
        
        gaps = research_gaps.get('research_gaps', [])
        if gaps:
            summary += f"{len(gaps)} candidate research gaps were identified based on limitations "
            summary += "and future work mentioned in the papers. "
        
        summary += "Detailed analysis follows below.\n"
        return summary
    
    def _generate_comparison_table(self, table_data: List[Dict]) -> str:
        """Generate Markdown comparison table."""
        if not table_data:
            return "No comparison data available.\n"
        
        headers = ["Paper", "Year", "Problem", "Methodology", "Dataset", "Metrics", "Findings", "Limitations"]
        table = "| " + " | ".join(headers) + " |\n"
        table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        for row in table_data:
            values = [
                row.get('title', 'N/A')[:30],
                str(row.get('year', 'N/A')),
                row.get('research_problem', 'N/A')[:30],
                row.get('methodology', 'N/A')[:30],
                row.get('dataset', 'N/A')[:20],
                row.get('evaluation_metrics', 'N/A')[:20],
                row.get('key_findings', 'N/A')[:30],
                row.get('limitations', 'N/A')[:30]
            ]
            table += "| " + " | ".join(values) + " |\n"
        
        return table
    
    def _generate_future_research(self, gaps: List[Dict]) -> str:
        """Generate future research directions section."""
        if not gaps:
            return "Based on the analyzed papers, specific future research directions should be derived from the limitations and future work sections of each individual paper.\n"
        
        directions = []
        for gap in gaps[:3]:  # Top 3 gaps
            if gap.get('research_question'):
                directions.append(f"- {gap['research_question']}")
        
        if directions:
            return "\n".join(directions) + "\n"
        return "Future research directions should address the identified research gaps above.\n"
