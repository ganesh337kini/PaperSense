"""
vision_service.py
Vision-LLM integration for analyzing figures and equations in research papers.
Uses OpenAI GPT-4o vision API when available; gracefully degrades otherwise.
"""

import base64
import os
from typing import Optional
from app.config import settings


class VisionService:
    """Service for AI-powered analysis of figures, charts, and equations."""

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
                print(f"[VisionService] Could not init OpenAI client: {e}")
                self.mock_mode = True

    def describe_figure(self, image_path: str, context: str = "") -> str:
        """
        Describe a figure or chart image for research context.

        Args:
            image_path: Absolute path to the PNG/JPG image.
            context: Optional surrounding text context from the paper.

        Returns:
            Human-readable description of the figure.
        """
        if self.mock_mode or self.client is None:
            return (
                "[Figure: visual content detected — configure OpenAI API key "
                "for AI-powered figure description]"
            )

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            ext = os.path.splitext(image_path)[1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"

            context_note = f"\n\nContext from the paper: {context[:500]}" if context else ""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "You are analyzing a figure from a research paper. "
                                    "Describe what this figure shows, including: the type of chart/diagram, "
                                    "what axes or labels are present, key trends or findings visible, "
                                    "and any notable values. Be concise and precise."
                                    + context_note
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{image_data}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"[Figure description unavailable: {str(e)}]"

    def analyze_equation(self, latex_or_text: str) -> str:
        """
        Analyze and explain a mathematical equation.

        Args:
            latex_or_text: Raw equation text or LaTeX.

        Returns:
            Clean LaTeX representation and plain-English explanation.
        """
        if self.mock_mode or self.client is None:
            return latex_or_text  # Return as-is in mock mode

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a mathematical notation expert. Given an equation or formula "
                            "from a research paper, output clean LaTeX and a brief plain-English explanation."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Convert and explain this equation from a paper:\n\n{latex_or_text}\n\n"
                            "Respond with:\nLaTeX: <latex>\nExplanation: <explanation>"
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return latex_or_text  # Fallback to original text
