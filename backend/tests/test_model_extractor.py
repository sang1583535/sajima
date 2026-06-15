from backend.models.schemas import DatasetCandidate, Paper
from backend.services.candidate_merger import merge_candidates
from backend.services.model_extractor import (
    extract_candidates_with_gliner,
    is_model_extractor_available,
    select_relevant_chunks,
)


def test_select_relevant_chunks_returns_keyword_chunks() -> None:
    text = (
        "Intro paragraph.\n\n"
        "We introduce Hanfu-Bench, a benchmark for cultural understanding.\n\n"
        "Another paragraph.\n\n"
        "This dataset is specifically designed for evaluation.\n\n"
        "Final paragraph."
    )

    chunks = select_relevant_chunks(text, max_chunks=4)

    assert len(chunks) == 2
    assert any("Hanfu-Bench" in chunk for chunk in chunks)
    assert any("dataset" in chunk.lower() for chunk in chunks)


def test_select_relevant_chunks_limits_number_of_chunks() -> None:
    text = "\n\n".join(
        [f"Paragraph {index} about a dataset benchmark." for index in range(12)]
    )

    chunks = select_relevant_chunks(text, max_chunks=3)

    assert len(chunks) == 3


def test_extract_candidates_with_gliner_returns_empty_when_unavailable(monkeypatch) -> None:
    paper = Paper(paper_id="paper-1", title="Hanfu-Bench: A Multimodal Benchmark")
    monkeypatch.setattr("backend.services.model_extractor.get_gliner_model", lambda: None)

    candidates = extract_candidates_with_gliner(
        "We introduce Hanfu-Bench, a benchmark for cultural understanding.",
        paper,
        evidence_source="gliner_metadata",
    )

    assert candidates == []


def test_extract_candidates_with_gliner_uses_mock_model(monkeypatch) -> None:
    class DummyModel:
        def predict_entities(self, text, labels, threshold=0.35):
            return [
                {"text": "Hanfu-Bench", "label": "dataset", "score": 0.91},
                {"text": "Our", "label": "benchmark", "score": 0.10},
            ]

    paper = Paper(paper_id="paper-2", title="Hanfu-Bench: A Multimodal Benchmark")
    monkeypatch.setattr("backend.services.model_extractor.get_gliner_model", lambda: DummyModel())

    candidates = extract_candidates_with_gliner(
        "We introduce Hanfu-Bench, a benchmark for cultural understanding.",
        paper,
        evidence_source="gliner_metadata",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.name == "Hanfu-Bench"
    assert candidate.evidence_source == "gliner_metadata"
    assert candidate.extraction_method == "gliner"
    assert candidate.confidence == "medium"


def test_merge_candidates_merges_duplicates() -> None:
    paper_id = "paper-3"
    rule_candidate = DatasetCandidate(
        name="Hanfu-Bench",
        source_title="Hanfu-Bench: A Multimodal Benchmark",
        source_paper_id=paper_id,
        evidence="We introduce Hanfu-Bench, a benchmark for cultural understanding.",
        evidence_source="metadata",
        score=4.0,
        extraction_method="rule",
        confidence="high",
        validation_reasons=["rule-based pattern"],
    )
    model_candidate = DatasetCandidate(
        name="Hanfu-Bench",
        source_title="Hanfu-Bench: A Multimodal Benchmark",
        source_paper_id=paper_id,
        evidence="Hanfu-Bench benchmark.",
        evidence_source="gliner_metadata",
        score=1.0,
        extraction_method="gliner",
        confidence="medium",
        validation_reasons=["GLiNER label: dataset"],
    )

    merged = merge_candidates([rule_candidate], [model_candidate])

    assert len(merged) == 1
    candidate = merged[0]
    assert candidate.extraction_method == "rule+gliner"
    assert candidate.score >= 6.0
    assert "rule-based pattern" in candidate.validation_reasons
    assert "GLiNER label: dataset" in candidate.validation_reasons


def test_model_extractor_availability_is_safe() -> None:
    assert isinstance(is_model_extractor_available(), bool)
