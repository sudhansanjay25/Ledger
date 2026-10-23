import io
import re
from typing import Dict, Any, Union

import pypdf


def validate_pdf_bytes(file_bytes: bytes) -> bool:
    """Verifies that the byte stream starts with standard PDF magic bytes."""
    return file_bytes.startswith(b"%PDF-")


def compute_text_quality(text: str) -> Dict[str, Any]:
    """
    Computes reading quality score and readability metrics for text.
    Returns quality_score (0.0 to 1.0) and is_readable (boolean).
    """
    cleaned = re.sub(r'\s+', ' ', text).strip()
    words = cleaned.split()
    if not words:
        return {
            "cleaned_text": "",
            "quality_score": 0.0,
            "is_readable": False,
            "total_words": 0,
            "readable_words": 0
        }

    alphabetic_words = [
        w for w in words
        if w.isalpha() or (len(w) > 1 and w[:-1].isalpha() and w[-1] in ['.', ',', ';', ':', '!', '?'])
    ]
    quality_score = len(alphabetic_words) / len(words)
    is_readable = quality_score >= 0.5

    return {
        "cleaned_text": cleaned,
        "quality_score": round(quality_score, 2),
        "is_readable": is_readable,
        "total_words": len(words),
        "readable_words": len(alphabetic_words)
    }


def extract_text_from_pdf(pdf_source: Union[str, bytes, io.BytesIO]) -> Dict[str, Any]:
    """
    Extracts text from a PDF file path or byte stream using pypdf.
    Computes quality metrics and detects degraded/scanned content.
    """
    if isinstance(pdf_source, str):
        with open(pdf_source, "rb") as f:
            pdf_bytes = f.read()
    elif isinstance(pdf_source, bytes):
        pdf_bytes = pdf_source
    elif isinstance(pdf_source, io.BytesIO):
        pdf_bytes = pdf_source.getvalue()
    else:
        raise ValueError("Unsupported PDF source type. Must be file path, bytes, or BytesIO.")

    if not validate_pdf_bytes(pdf_bytes):
        return {
            "success": False,
            "error": "Invalid file format: Missing %PDF- magic bytes signature.",
            "text": "",
            "page_count": 0,
            "quality_score": 0.0,
            "is_readable": False
        }

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        page_count = len(reader.pages)
        pages_text = []

        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            pages_text.append(page_text.strip())

        full_text = "\n\n".join([pt for pt in pages_text if pt])
        metrics = compute_text_quality(full_text)

        return {
            "success": True,
            "error": None,
            "text": full_text,
            "page_count": page_count,
            "quality_score": metrics["quality_score"],
            "is_readable": metrics["is_readable"] and len(full_text.strip()) > 30,
            "total_words": metrics["total_words"],
            "readable_words": metrics["readable_words"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"PDF parsing error: {str(e)}",
            "text": "",
            "page_count": 0,
            "quality_score": 0.0,
            "is_readable": False
        }
