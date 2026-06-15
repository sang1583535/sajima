from __future__ import annotations

import re

from backend.models.schemas import DatasetCandidate
from backend.services.dataset_extractor import is_valid_candidate_name, looks_like_dataset_name


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[A-Za-z0-9_\-]+", text.lower()) if token}


def rank_candidates(query: str, candidates: list[DatasetCandidate]) -> list[DatasetCandidate]:
    query_tokens = tokenize(query)
    ranked: list[DatasetCandidate] = []

    for candidate in candidates:
        if not is_valid_candidate_name(candidate.name):
            continue

        score = 0.0
        name_tokens = tokenize(candidate.name)
        evidence_tokens = tokenize(candidate.evidence)
        title_tokens = tokenize(candidate.source_title)

        if query_tokens & name_tokens:
            score += 3.0
        if query_tokens & evidence_tokens:
            score += 2.0
        if query_tokens & title_tokens:
            score += 2.0

        if looks_like_dataset_name(candidate.name):
            score += 2.0

        if candidate.extraction_method == "rule+gliner":
            score += 2.0
        elif candidate.extraction_method == "gliner":
            score += 0.75

        evidence_lower = candidate.evidence.lower()
        if candidate.evidence_source == "title":
            score += 3.0
        elif evidence_lower.startswith("we introduce") or evidence_lower.startswith("we present") or evidence_lower.startswith("we propose"):
            score += 2.5

        if "dataset" in evidence_lower:
            score += 2.0
        if "benchmark" in evidence_lower:
            score += 2.0
        if "corpus" in evidence_lower:
            score += 1.5
        if candidate.evidence_source == "pdf":
            score += 1.0
        if candidate.year is not None and candidate.year >= 2023:
            score += 1.0

        ranked.append(candidate.model_copy(update={"score": score}))

    return sorted(ranked, key=lambda item: item.score, reverse=True)
