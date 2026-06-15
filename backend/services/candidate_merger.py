from __future__ import annotations

from backend.models.schemas import DatasetCandidate


def _merge_validation_reasons(left: list[str], right: list[str]) -> list[str]:
    combined: list[str] = []
    for reason in left + right:
        if reason and reason not in combined:
            combined.append(reason)
    return combined


def _choose_better_candidate(existing: DatasetCandidate, new_candidate: DatasetCandidate) -> DatasetCandidate:
    existing_evidence = existing.evidence.strip()
    new_evidence = new_candidate.evidence.strip()

    preferred = existing
    if len(new_evidence) < len(existing_evidence):
        preferred = new_candidate

    validation_reasons = _merge_validation_reasons(existing.validation_reasons, new_candidate.validation_reasons)
    extraction_method = existing.extraction_method
    if existing.extraction_method != new_candidate.extraction_method:
        extraction_method = "rule+gliner"

    confidence = existing.confidence
    if preferred is new_candidate:
        confidence = new_candidate.confidence

    return preferred.model_copy(
        update={
            "score": max(existing.score, new_candidate.score) + 2.0,
            "validation_reasons": validation_reasons,
            "extraction_method": extraction_method,
            "confidence": confidence,
        }
    )


def merge_candidates(
    rule_candidates: list[DatasetCandidate],
    model_candidates: list[DatasetCandidate],
) -> list[DatasetCandidate]:
    merged: dict[tuple[str, str], DatasetCandidate] = {}

    for candidate in rule_candidates + model_candidates:
        key = (candidate.name.lower(), candidate.source_paper_id)
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
            continue

        merged[key] = _choose_better_candidate(existing, candidate)

    return list(merged.values())
