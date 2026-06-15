from backend.models.schemas import DatasetCandidate
from backend.services.ranker import rank_candidates, tokenize


def test_tokenize_splits_query_terms() -> None:
    assert tokenize("Cultural understanding in VLMs") == {"cultural", "understanding", "in", "vlms"}


def test_rank_candidates_prefers_title_and_introduction_patterns() -> None:
    candidates = [
        DatasetCandidate(
            name="Hanfu-Bench",
            source_title="Hanfu-Bench: A Multimodal Benchmark on Cross-Temporal Cultural Understanding",
            source_paper_id="p1",
            year=2024,
            evidence="We introduce Hanfu-Bench, a manually curated multimodal dataset.",
            evidence_source="title",
        ),
        DatasetCandidate(
            name="CulturalVQA",
            source_title="Some Other Paper",
            source_paper_id="p2",
            year=2020,
            evidence="We describe a method evaluated on CulturalVQA.",
            evidence_source="metadata",
        ),
    ]

    ranked = rank_candidates("cultural benchmark", candidates)
    assert ranked[0].name == "Hanfu-Bench"
    assert ranked[0].score > ranked[1].score


def test_rank_candidates_filters_generic_names() -> None:
    candidates = [
        DatasetCandidate(
            name="Our",
            source_title="Paper",
            source_paper_id="p3",
            evidence="Our benchmark provides...",
            evidence_source="metadata",
        ),
        DatasetCandidate(
            name="MMLU",
            source_title="Paper",
            source_paper_id="p4",
            evidence="We evaluate on MMLU.",
            evidence_source="metadata",
        ),
    ]

    ranked = rank_candidates("benchmark", candidates)
    assert len(ranked) == 1
    assert ranked[0].name == "MMLU"
