"""
layout_parser.py
Layout-aware PDF parsing using PyMuPDF rawdict extraction.
Extracts text blocks with bounding boxes, classifies block types
(text, equation, table, figure), and detects sections.
"""

import pymupdf as fitz
from pathlib import Path
from typing import List, Dict, Optional
import re
import os


# Symbols commonly found in mathematical equations
MATH_SYMBOLS = set("∑∫∂∇≈≤≥±×÷√∞αβγδεζηθλμπσφψωΓΔΘΛΞΠΣΦΨΩ")
MATH_KEYWORDS = {"equation", "theorem", "lemma", "proof", "corollary", "proposition"}
SECTION_NAMES = [
    "abstract", "introduction", "related work", "background",
    "methodology", "method", "methods", "approach", "model",
    "experiment", "experiments", "results", "evaluation",
    "discussion", "conclusion", "conclusions", "future work",
    "references", "bibliography", "acknowledgement", "acknowledgements",
    "appendix",
]


class LayoutParser:
    """Layout-aware PDF parser that extracts blocks with bounding boxes."""

    def extract_with_layout(self, file_path: str) -> List[Dict]:
        """
        Extract text blocks with layout metadata from a PDF.

        Args:
            file_path: Path to the PDF file.

        Returns:
            List of dicts: {text, page_number, bbox_x0, bbox_y0, bbox_x1,
                            bbox_y1, block_type, section}
        """
        results: List[Dict] = []
        try:
            doc = fitz.open(file_path)
            current_section = "Unknown"

            for page_index in range(len(doc)):
                page = doc[page_index]
                page_num = page_index + 1

                # Use rawdict for span-level detail with bounding boxes
                raw = page.get_text("rawdict")
                blocks = raw.get("blocks", [])

                for block in blocks:
                    btype = block.get("type", 0)

                    # type 1 = image block — record as figure placeholder
                    if btype == 1:
                        bbox = block.get("bbox", (0, 0, 0, 0))
                        results.append({
                            "text": "[Figure/Image]",
                            "page_number": page_num,
                            "bbox_x0": bbox[0],
                            "bbox_y0": bbox[1],
                            "bbox_x1": bbox[2],
                            "bbox_y1": bbox[3],
                            "block_type": "figure",
                            "section": current_section,
                        })
                        continue

                    # type 0 = text block
                    lines = block.get("lines", [])
                    block_text_parts = []
                    for line in lines:
                        spans = line.get("spans", [])
                        for span in spans:
                            txt = span.get("text", "")
                            if txt.strip():
                                block_text_parts.append(txt)

                    block_text = " ".join(block_text_parts).strip()
                    if not block_text:
                        continue

                    bbox = block.get("bbox", (0, 0, 0, 0))

                    # Update running section detection
                    detected = self._detect_section(block_text)
                    if detected != "Unknown":
                        current_section = detected

                    block_type = self._classify_block(block_text, block)

                    results.append({
                        "text": block_text,
                        "page_number": page_num,
                        "bbox_x0": round(bbox[0], 2),
                        "bbox_y0": round(bbox[1], 2),
                        "bbox_x1": round(bbox[2], 2),
                        "bbox_y1": round(bbox[3], 2),
                        "block_type": block_type,
                        "section": current_section,
                    })

            doc.close()
        except Exception as e:
            print(f"[LayoutParser] Warning: layout extraction failed: {e}")

        return results

    def _classify_block(self, text: str, block: Optional[Dict] = None) -> str:
        """
        Classify a text block as text | equation | table | figure.
        Uses heuristic symbol and pattern detection.
        """
        # Equation detection
        math_char_count = sum(1 for ch in text if ch in MATH_SYMBOLS)
        has_latex = bool(re.search(r"\\[a-zA-Z]+|\\\\|\$[^$]+\$", text))
        has_math_kw = any(kw in text.lower() for kw in MATH_KEYWORDS)
        unusual_font = False

        if block:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 12)
                    if size < 8 or size > 20:
                        unusual_font = True

        if math_char_count >= 2 or has_latex or (has_math_kw and unusual_font):
            return "equation"

        # Table detection — multiple lines with tab/pipe/spacing patterns
        lines = text.split("\n")
        if len(lines) >= 2:
            tab_lines = sum(1 for ln in lines if "\t" in ln or "  " in ln or "|" in ln)
            if tab_lines >= 2:
                return "table"

        # Check for table-like numeric patterns across lines
        num_lines_with_numbers = sum(
            1 for ln in lines if re.search(r"\d+\.\d+|\d+%|\d+\s+\d+", ln)
        )
        if num_lines_with_numbers >= 3 and len(lines) >= 3:
            return "table"

        return "text"

    def _detect_section(self, text: str) -> str:
        """
        Detect if this block is a section header and return the section name.
        Returns 'Unknown' if not a section header.
        """
        # Section headers are typically short, possibly numbered
        first_line = text.split("\n")[0].strip()
        if len(first_line) > 80:
            return "Unknown"

        # Strip numbering like "1.", "2.1", "I.", etc.
        clean = re.sub(r"^[\dIVXivx]+[\.\d]*\.?\s*", "", first_line).strip().lower()

        for section in SECTION_NAMES:
            if clean == section or clean.startswith(section):
                return first_line[:60]

        return "Unknown"

    def extract_figures(self, file_path: str, output_dir: str) -> List[Dict]:
        """
        Extract figures/images from PDF pages as PNG files.

        Args:
            file_path: Path to PDF.
            output_dir: Directory to save figure images.

        Returns:
            List of {page_number, image_path, bbox_x0, bbox_y0, bbox_x1, bbox_y1}
        """
        figures = []
        try:
            os.makedirs(output_dir, exist_ok=True)
            doc = fitz.open(file_path)
            fig_index = 0

            for page_index in range(len(doc)):
                page = doc[page_index]
                page_num = page_index + 1

                raw = page.get_text("rawdict")
                for block in raw.get("blocks", []):
                    if block.get("type") == 1:  # image block
                        bbox = block.get("bbox", (0, 0, 0, 0))
                        rect = fitz.Rect(bbox)
                        try:
                            pix = page.get_pixmap(clip=rect, dpi=150)
                            img_path = os.path.join(
                                output_dir, f"fig_p{page_num}_{fig_index}.png"
                            )
                            pix.save(img_path)
                            figures.append({
                                "page_number": page_num,
                                "image_path": img_path,
                                "bbox_x0": round(bbox[0], 2),
                                "bbox_y0": round(bbox[1], 2),
                                "bbox_x1": round(bbox[2], 2),
                                "bbox_y1": round(bbox[3], 2),
                            })
                            fig_index += 1
                        except Exception as e:
                            print(f"[LayoutParser] Could not extract figure: {e}")

            doc.close()
        except Exception as e:
            print(f"[LayoutParser] Figure extraction failed: {e}")

        return figures
