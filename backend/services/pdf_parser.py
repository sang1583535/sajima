from __future__ import annotations

try:
    import fitz
except ImportError:  # pragma: no cover - dependency may be absent in local validation environments
    fitz = None


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def extract_text_from_pdf(pdf_path: str, max_pages: int = 12) -> str:
    """Extract text from the first pages of a PDF using PyMuPDF."""
    if fitz is None:
        return ""
    try:
        document = fitz.open(pdf_path)
        try:
            parts: list[str] = []
            page_limit = min(max_pages, document.page_count)
            for page_index in range(page_limit):
                page = document.load_page(page_index)
                text = page.get_text("text")
                if text:
                    parts.append(text)
            return normalize_whitespace("\n".join(parts))
        finally:
            document.close()
    except Exception:
        return ""
