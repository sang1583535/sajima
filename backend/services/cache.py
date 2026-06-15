import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).resolve().parents[2]
_CACHE_DIR = Path(os.environ.get("CACHE_DIR", str(_ROOT / ".cache"))) / "papers"
_USE_CACHE = os.environ.get("USE_CACHE", "true").strip().lower() not in {"false", "0", "no"}


def _cache_key(query: str, max_papers: int, provider: str = "default") -> str:
    raw_key = f"{provider.strip().lower()}::{query.strip().lower()}::{max_papers}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _cache_file_path(query: str, max_papers: int, provider: str = "default") -> Path:
    return _CACHE_DIR / f"{_cache_key(query, max_papers, provider)}.json"


def load_cached_papers(query: str, max_papers: int, provider: str = "default") -> dict | None:
    """Load raw cached paper search JSON if available."""
    if not _USE_CACHE:
        return None
    try:
        file_path = _cache_file_path(query, max_papers, provider)
        if not file_path.exists():
            return None
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_cached_papers(query: str, max_papers: int, data: dict, provider: str = "default") -> None:
    """Save raw paper search JSON to local cache."""
    if not _USE_CACHE:
        return
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = _cache_file_path(query, max_papers, provider)
        file_path.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        return
