from __future__ import annotations

import os
import re
from pathlib import Path
from types import SimpleNamespace

try:
    import requests
except ImportError:  # pragma: no cover - dependency may be absent in local validation environments
    requests = SimpleNamespace(get=None)


def _cache_dir() -> Path:
    return Path(os.environ.get("CACHE_DIR", ".cache")) / "pdfs"


def _sanitize_paper_id(paper_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", paper_id.strip()) or "paper"


def download_pdf(pdf_url: str, paper_id: str) -> str | None:
    """Download an open-access PDF into the local cache.

    Returns the cached file path as a string. Any download or validation failure
    returns None so the search pipeline can continue.
    """
    if not pdf_url or not paper_id:
        return None

    cache_dir = _cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = cache_dir / f"{_sanitize_paper_id(paper_id)}.pdf"
    if pdf_path.exists():
        return str(pdf_path)

    try:
        if requests.get is None:
            return None
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if content_type and "pdf" not in content_type.lower():
            return None
        pdf_path.write_bytes(response.content)
        return str(pdf_path)
    except Exception:
        if pdf_path.exists():
            try:
                pdf_path.unlink()
            except Exception:
                pass
        return None
