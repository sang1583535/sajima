from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from backend.models.schemas import DatasetCandidate, Paper
from backend.services.dataset_extractor import is_valid_candidate_name

MODEL_NAME = "urchade/gliner_medium-v2.1"
DATASET_KEYWORDS = [
    "dataset",
    "datasets",
    "benchmark",
    "benchmarks",
    "corpus",
    "corpora",
    "evaluation set",
    "test set",
    "training set",
    "validation set",
]
_ROOT = Path(__file__).resolve().parents[2]
_MODEL_CACHE_DIR = _ROOT / ".models"
_HF_CACHE_DIR = _MODEL_CACHE_DIR / "huggingface"
_MODEL = None


def _configure_model_cache() -> None:
    _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(_HF_CACHE_DIR))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(_HF_CACHE_DIR / "transformers"))
    os.environ.setdefault("HF_HUB_CACHE", str(_HF_CACHE_DIR / "hub"))


def is_model_extractor_available() -> bool:
    try:
        from gliner import GLiNER  # type: ignore
    except ImportError:
        return False
    return GLiNER is not None


def get_gliner_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    try:
        from gliner import GLiNER  # type: ignore
    except ImportError:
        return None

    _configure_model_cache()

    try:
        _MODEL = GLiNER.from_pretrained(MODEL_NAME)
    except Exception:
        _MODEL = None
    return _MODEL


def select_relevant_chunks(text: str, max_chunks: int = 8) -> list[str]:
    cleaned = "\n".join(line.strip() for line in text.splitlines())
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", cleaned) if paragraph.strip()]
    if not paragraphs:
        paragraphs = [" ".join(text.split())] if text.strip() else []

    chunks: list[str] = []
    for paragraph in paragraphs:
        lower = paragraph.lower()
        if not any(keyword in lower for keyword in DATASET_KEYWORDS):
            continue
        chunk = paragraph[:1600].strip()
        if chunk:
            chunks.append(chunk)
        if len(chunks) >= max_chunks:
            break
    return chunks[:max_chunks]


def _truncate_evidence(text: str, limit: int = 500) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _entity_text(entity: Any) -> str:
    if isinstance(entity, dict):
        value = entity.get("text") or entity.get("entity") or entity.get("name")
        return str(value) if value is not None else ""
    return str(getattr(entity, "text", "") or getattr(entity, "entity", "") or getattr(entity, "name", ""))


def _entity_score(entity: Any) -> float:
    if isinstance(entity, dict):
        value = entity.get("score", 0.0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    value = getattr(entity, "score", 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _chunk_contains_entity(chunk: str, entity_text: str) -> str:
    if not entity_text:
        return _truncate_evidence(chunk)
    lower_chunk = chunk.lower()
    lower_entity = entity_text.lower()
    index = lower_chunk.find(lower_entity)
    if index == -1:
        return _truncate_evidence(chunk)
    start = max(0, index - 180)
    end = min(len(chunk), index + len(entity_text) + 220)
    return _truncate_evidence(chunk[start:end])


def extract_candidates_with_gliner(
    text: str,
    paper: Paper,
    evidence_source: str,
    max_chunks: int = 8,
) -> list[DatasetCandidate]:
    if not text.strip():
        return []

    model = get_gliner_model()
    if model is None:
        return []

    chunks = select_relevant_chunks(text, max_chunks=max_chunks)
    if not chunks:
        return []

    labels = ["dataset", "benchmark", "corpus"]
    candidates: dict[str, DatasetCandidate] = {}

    for chunk in chunks:
        try:
            entities = model.predict_entities(chunk, labels, threshold=0.35)
        except Exception:
            continue

        for entity in entities or []:
            name = _entity_text(entity).strip()
            if not is_valid_candidate_name(name):
                continue

            evidence = _chunk_contains_entity(chunk, name)
            key = name.lower()
            score = _entity_score(entity)
            new_candidate = DatasetCandidate(
                name=name,
                source_title=paper.title,
                source_paper_id=paper.paper_id,
                year=paper.year,
                evidence=evidence,
                evidence_source=evidence_source,
                paper_url=paper.url,
                pdf_url=paper.open_access_pdf_url,
                score=score,
                extraction_method="gliner",
                confidence="medium",
                validation_reasons=[f"GLiNER label: {getattr(entity, 'label', entity.get('label') if isinstance(entity, dict) else '')}".strip()],
            )
            existing = candidates.get(key)
            if existing is None or len(new_candidate.evidence) < len(existing.evidence):
                candidates[key] = new_candidate

    return list(candidates.values())
