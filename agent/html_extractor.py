import re
from typing import Dict, Any, Union
from bs4 import BeautifulSoup
from pdf_extractor import compute_text_quality


def extract_text_from_html(html_source: Union[str, bytes]) -> Dict[str, Any]:
    """
    Parses and sanitizes HTML-formatted regulatory documents using BeautifulSoup.
    Strips scripts, styles, metadata, and invisible elements while preserving
    document structure, headings, and readability.
    """
    if isinstance(html_source, bytes):
        try:
            html_text = html_source.decode("utf-8")
        except UnicodeDecodeError:
            html_text = html_source.decode("latin-1", errors="ignore")
    elif isinstance(html_source, str):
        html_text = html_source
    else:
        raise ValueError("html_source must be str or bytes.")

    if not html_text.strip():
        return {
            "success": False,
            "error": "Empty HTML content provided.",
            "title": "",
            "text": "",
            "quality_score": 0.0,
            "is_readable": False,
            "total_words": 0,
            "readable_words": 0
        }

    try:
        soup = BeautifulSoup(html_text, "html.parser")

        # 1. Extract title before stripping tags
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find(["h1", "h2"]):
            title = soup.find(["h1", "h2"]).get_text().strip()

        # 2. Decompose dangerous and non-content tags
        unwanted_tags = [
            "script", "style", "noscript", "iframe", "object",
            "embed", "svg", "canvas", "nav", "footer", "meta", "link"
        ]
        for tag in soup.find_all(unwanted_tags):
            tag.decompose()

        # 3. Add spacing around block-level elements to preserve text flow
        block_tags = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "li", "tr", "section", "article"]
        for block in soup.find_all(block_tags):
            block.insert_after("\n\n")

        # 4. Extract clean plain text
        raw_text = soup.get_text(separator=" ")
        
        # 5. Clean excess whitespace and blank lines
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in raw_text.splitlines()]
        cleaned_text = "\n".join([line for line in lines if line])

        # 6. Calculate reading quality score
        metrics = compute_text_quality(cleaned_text)

        return {
            "success": True,
            "error": None,
            "title": title or "Regulatory Circular Notice",
            "text": cleaned_text,
            "quality_score": metrics["quality_score"],
            "is_readable": metrics["is_readable"] and metrics["total_words"] > 15,
            "total_words": metrics["total_words"],
            "readable_words": metrics["readable_words"]
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"HTML parsing error: {str(exc)}",
            "title": "",
            "text": "",
            "quality_score": 0.0,
            "is_readable": False,
            "total_words": 0,
            "readable_words": 0
        }
