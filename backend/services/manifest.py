from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


def safe_query_folder_name(query: str, max_length: int = 80) -> str:
    normalized = query.strip().lower()
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"[^a-z0-9\-]", "", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if not normalized:
        normalized = "query"
    return normalized[:max_length].rstrip("-") or "query"


def save_trend_manifest(query: str, response_data: dict) -> str:
    """Save a trend analysis manifest and return its file path.

    The API should never fail due to manifest persistence issues, so this
    function returns an empty string on any save failure.
    """
    try:
        today = date.today().isoformat()
        query_folder = safe_query_folder_name(query)
        manifest_dir = PROCESSED_DIR / today / query_folder
        manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = manifest_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(response_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(manifest_path)
    except Exception:
        return ""
