from backend.models.schemas import Author, Paper
from backend.services.trend_analyzer import (
    analyze_trends,
    build_trend_summary,
    compute_all_category_counts,
    compute_primary_category_counts,
    compute_yearly_counts,
    extract_top_keywords,
    suggest_query_terms,
)


def _paper(
    paper_id: str,
    title: str,
    year: int | None,
    primary_category: str | None,
    categories: list[str],
    abstract: str | None = None,
    pdf_url: str | None = None,
) -> Paper:
    return Paper(
        paper_id=paper_id,
        title=title,
        abstract=abstract,
        year=year,
        authors=[Author(name="A")],
        venue="arXiv",
        url=f"https://example.org/{paper_id}",
        open_access_pdf_url=pdf_url,
        source="arxiv",
        published_date=f"{year}-01-01" if year else None,
        primary_category=primary_category,
        categories=categories,
    )


def test_compute_yearly_counts_sorted_and_ignores_missing() -> None:
    papers = [
        _paper("p1", "Paper one", 2022, "cs.CL", ["cs.CL"]),
        _paper("p2", "Paper two", None, "cs.CL", ["cs.CL"]),
        _paper("p3", "Paper three", 2021, "cs.CV", ["cs.CV"]),
        _paper("p4", "Paper four", 2022, "cs.AI", ["cs.AI"]),
    ]

    yearly = compute_yearly_counts(papers)
    assert yearly == [{"year": 2021, "count": 1}, {"year": 2022, "count": 2}]


def test_compute_primary_category_counts() -> None:
    papers = [
        _paper("p1", "A", 2022, "cs.CL", ["cs.CL"]),
        _paper("p2", "B", 2022, "cs.CV", ["cs.CV"]),
        _paper("p3", "C", 2021, "cs.CL", ["cs.CL", "cs.AI"]),
        _paper("p4", "D", 2021, None, ["cs.AI"]),
    ]

    counts = compute_primary_category_counts(papers)
    assert counts[0] == {"category": "cs.CL", "count": 2}
    assert {"category": "cs.CV", "count": 1} in counts


def test_compute_all_category_counts() -> None:
    papers = [
        _paper("p1", "A", 2022, "cs.CL", ["cs.CL", "cs.AI"]),
        _paper("p2", "B", 2022, "cs.CV", ["cs.CV", "cs.AI"]),
        _paper("p3", "C", 2021, "cs.CL", ["cs.CL"]),
    ]

    counts = compute_all_category_counts(papers)
    assert counts[0] == {"category": "cs.AI", "count": 2}
    assert {"category": "cs.CL", "count": 2} in counts
    assert {"category": "cs.CV", "count": 1} in counts


def test_extract_top_keywords_removes_stopwords() -> None:
    papers = [
        _paper(
            "p1",
            "Multilingual Vision Benchmark",
            2022,
            "cs.CV",
            ["cs.CV"],
            abstract="This benchmark for vision and language uses multilingual data and robust evaluation.",
        )
    ]

    keywords = extract_top_keywords(papers, top_k=10)
    words = {item["keyword"] for item in keywords}

    assert "multilingual" in words
    assert "vision" in words
    assert "benchmark" in words
    assert "this" not in words
    assert "and" not in words


def test_build_trend_summary_handles_empty() -> None:
    summary = build_trend_summary([])
    assert summary == {
        "total_papers": 0,
        "year_min": None,
        "year_max": None,
        "most_common_primary_category": None,
        "paper_count_with_pdf": 0,
    }


def test_analyze_trends_shape() -> None:
    papers = [
        _paper("p1", "COCO dataset benchmark", 2023, "cs.CV", ["cs.CV"], pdf_url="https://example.org/p1.pdf")
    ]

    trend = analyze_trends(papers, top_k_keywords=5)
    assert set(trend.keys()) == {
        "summary",
        "yearly_counts",
        "primary_category_counts",
        "category_counts",
        "top_keywords",
        "suggested_query_terms",
    }
    assert trend["summary"]["total_papers"] == 1


def test_suggest_query_terms_limits_and_deduplicates() -> None:
    top_keywords = [
        {"keyword": "vision", "count": 5},
        {"keyword": "language", "count": 4},
        {"keyword": "vision", "count": 3},
        {"keyword": "benchmark", "count": 2},
    ]

    suggestions = suggest_query_terms(top_keywords, max_terms=3)
    assert suggestions == ["vision", "language", "benchmark"]
