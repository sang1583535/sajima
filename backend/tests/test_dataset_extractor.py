from backend.models.schemas import Paper
from backend.services.dataset_extractor import (
    extract_candidate_names,
    extract_candidate_names_from_title,
    extract_dataset_candidates_from_text,
    is_dataset_related_sentence,
    is_valid_candidate_name,
    looks_like_dataset_name,
)


def test_extract_hanfu_bench_from_title() -> None:
    title = "Hanfu-Bench: A Multimodal Benchmark on Cross-Temporal Cultural Understanding"
    assert "Hanfu-Bench" in extract_candidate_names_from_title(title)


def test_filter_generic_candidates() -> None:
    assert not is_valid_candidate_name("Our")
    assert not is_valid_candidate_name("This")
    assert not is_valid_candidate_name("Multimodal")


def test_extract_we_introduce_dataset() -> None:
    text = "To bridge this gap, we introduce Hanfu-Bench, a manually curated multimodal dataset."
    paper = Paper(
        paper_id="paper-1",
        title="Hanfu-Bench: A Multimodal Benchmark on Cultural Understanding",
    )
    candidates = extract_dataset_candidates_from_text(text, paper, evidence_source="metadata")
    names = [candidate.name for candidate in candidates]
    assert "Hanfu-Bench" in names


def test_keep_known_style_names() -> None:
    assert is_valid_candidate_name("CulturalVQA")
    assert is_valid_candidate_name("Multi3Hate")
    assert is_valid_candidate_name("MMLU")
    assert is_valid_candidate_name("ImageNet")


def test_looks_like_dataset_name_rules() -> None:
    assert looks_like_dataset_name("Hanfu-Bench")
    assert looks_like_dataset_name("MMLU")
    assert looks_like_dataset_name("CulturalVQA")
    assert not looks_like_dataset_name("Multimodal")
    assert not looks_like_dataset_name("Our")


def test_sentence_helpers() -> None:
    sentence = "We introduce CulturalVQA, a benchmark for cultural understanding."
    assert is_dataset_related_sentence(sentence)
    assert "CulturalVQA" in extract_candidate_names(sentence)
    assert "Dataset" not in extract_candidate_names("We introduce Dataset, a benchmark.")
