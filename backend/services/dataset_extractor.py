from __future__ import annotations

import re

from backend.models.schemas import DatasetCandidate, Paper

DATASET_KEYWORDS = [
    "dataset",
    "datasets",
    "benchmark",
    "benchmarks",
    "corpus",
    "corpora",
    "collection",
    "evaluation set",
    "test set",
    "training set",
    "validation set",
    "databases",
]

GENERIC_CANDIDATES = {
    "This",
    "These",
    "That",
    "Those",
    "Our",
    "The",
    "A",
    "An",
    "Dataset",
    "Datasets",
    "Benchmark",
    "Benchmarks",
    "Corpus",
    "Corpora",
    "Collection",
    "Database",
    "Databases",
    "Multimodal",
    "Multilingual",
    "Cultural",
    "Visual",
    "Language",
    "Vision",
    "Text",
    "Image",
    "Model",
    "Models",
    "Task",
    "Tasks",
    "Method",
    "Methods",
    "Experiment",
    "Experiments",
    "Evaluation",
    "Result",
    "Results",
    "Table",
    "Figure",
    "Section",
    "Abstract",
}

PATTERNS = [
    r"we introduce\s+([A-Z][A-Za-z0-9_\-]+)\s*,\s+a\s+(?:dataset|benchmark|corpus)",
    r"we present\s+([A-Z][A-Za-z0-9_\-]+)\s*,\s+a\s+(?:dataset|benchmark|corpus)",
    r"we propose\s+([A-Z][A-Za-z0-9_\-]+)\s*,\s+a\s+(?:dataset|benchmark|corpus)",
    r"([A-Z][A-Za-z0-9_\-]+)\s+(?:dataset|benchmark|corpus)",
    r"(?:dataset|benchmark|corpus)\s+(?:called|named)?\s*([A-Z][A-Za-z0-9_\-]+)",
    r"(?:evaluated|trained|tested|fine-tuned|finetuned)\s+on\s+(?:the\s+)?([A-Z][A-Za-z0-9_\-]+)",
    r"(?:experiments|evaluation)\s+on\s+(?:the\s+)?([A-Z][A-Za-z0-9_\-]+)",
]

TITLE_PATTERNS = [
    r"^([A-Z][A-Za-z0-9_\-]+)\s*:\s+.*(?:benchmark|dataset|corpus)",
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    return [sentence.strip() for sentence in _SENTENCE_SPLIT.split(cleaned) if sentence.strip()]


def is_dataset_related_sentence(sentence: str) -> bool:
    sentence_lower = sentence.lower()
    return any(keyword in sentence_lower for keyword in DATASET_KEYWORDS)


def _clean_candidate_name(name: str) -> str:
    return name.strip().strip(".,;:()[]{}")


def looks_like_dataset_name(name: str) -> bool:
    cleaned = _clean_candidate_name(name)
    if not cleaned:
        return False
    if "-" in cleaned:
        return True
    if any(char.isdigit() for char in cleaned):
        return True
    if cleaned.isupper() and len(cleaned) >= 3:
        return True

    suffixes = ("Bench", "VQA", "QA", "Eval", "Set")
    if any(cleaned.endswith(suffix) for suffix in suffixes):
        return True

    has_upper = any(char.isupper() for char in cleaned)
    has_lower = any(char.islower() for char in cleaned)
    has_internal_upper = any(char.isupper() for char in cleaned[1:])
    if has_upper and has_lower and has_internal_upper and len(cleaned) >= 5:
        return True

    return False


def is_valid_candidate_name(name: str) -> bool:
    cleaned = _clean_candidate_name(name)
    if not cleaned:
        return False
    if len(cleaned) < 3:
        return False
    if cleaned in GENERIC_CANDIDATES:
        return False
    return looks_like_dataset_name(cleaned)


def extract_candidate_names(sentence: str) -> list[str]:
    names: list[str] = []
    for pattern in PATTERNS:
        for match in re.finditer(pattern, sentence, flags=re.IGNORECASE):
            candidate = _clean_candidate_name(match.group(1))
            if not is_valid_candidate_name(candidate):
                continue
            names.append(candidate)
    return names


def extract_candidate_names_from_title(title: str) -> list[str]:
    names: list[str] = []
    for pattern in TITLE_PATTERNS:
        match = re.match(pattern, title, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = _clean_candidate_name(match.group(1))
        if is_valid_candidate_name(candidate):
            names.append(candidate)
    return names


def _truncate_evidence(sentence: str, limit: int = 500) -> str:
    sentence = sentence.strip()
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 3].rstrip() + "..."


def extract_dataset_candidates_from_text(
    text: str,
    paper: Paper,
    evidence_source: str,
) -> list[DatasetCandidate]:
    candidates: dict[str, DatasetCandidate] = {}

    def _upsert_candidate(
        name: str,
        evidence: str,
        evidence_source_value: str,
        extraction_method: str,
        validation_reason: str,
        confidence: str = "high",
    ) -> None:
        key = name.lower()
        existing = candidates.get(key)
        new_candidate = DatasetCandidate(
            name=name,
            source_title=paper.title,
            source_paper_id=paper.paper_id,
            year=paper.year,
            evidence=evidence,
            evidence_source=evidence_source_value,
            paper_url=paper.url,
            pdf_url=paper.open_access_pdf_url,
            extraction_method=extraction_method,
            confidence=confidence,
            validation_reasons=[validation_reason],
        )
        if existing is None:
            candidates[key] = new_candidate
            return

        existing_priority = 2 if existing.evidence_source == "title" else 1 if existing.evidence_source == "metadata" else 0
        new_priority = 2 if evidence_source_value == "title" else 1 if evidence_source_value == "metadata" else 0
        if new_priority > existing_priority or (
            new_priority == existing_priority and len(evidence) > len(existing.evidence)
        ):
            new_candidate.validation_reasons = list(dict.fromkeys(existing.validation_reasons + new_candidate.validation_reasons))
            candidates[key] = new_candidate
        else:
            existing.validation_reasons = list(dict.fromkeys(existing.validation_reasons + new_candidate.validation_reasons))

    for name in extract_candidate_names_from_title(paper.title):
        _upsert_candidate(name, _truncate_evidence(paper.title), "title", "rule", "title match")

    for sentence in split_sentences(text):
        if not is_dataset_related_sentence(sentence):
            continue

        evidence = _truncate_evidence(sentence)
        for name in extract_candidate_names(sentence):
            _upsert_candidate(name, evidence, evidence_source, "rule", "rule-based pattern")
    return list(candidates.values())
