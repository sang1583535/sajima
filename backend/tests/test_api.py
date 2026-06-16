import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_endpoint_with_monkeypatched_service(monkeypatch) -> None:
    from backend.models.schemas import Author, Paper

    def fake_search_papers(query: str, max_papers: int = 10) -> list[Paper]:
        assert query == "vision language datasets"
        assert max_papers == 2
        return [
            Paper(
                paper_id="paper-1",
                title="A Paper",
                abstract="Abstract",
                year=2024,
                authors=[Author(name="Alice")],
                venue="ACL",
                url="https://example.org/paper",
                open_access_pdf_url="https://example.org/paper.pdf",
            )
        ]

    monkeypatch.setattr("backend.api.routes.search_papers", fake_search_papers)
    monkeypatch.setattr("backend.api.routes.download_pdf", lambda pdf_url, paper_id: "/tmp/paper.pdf")
    monkeypatch.setattr(
        "backend.api.routes.extract_text_from_pdf",
        lambda pdf_path, max_pages=12: "We introduce CulturalVQA, a benchmark for cultural understanding.",
    )

    response = client.post(
        "/search",
        json={"query": "vision language datasets", "max_papers": 2, "extract_from_pdfs": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "vision language datasets"
    assert len(payload["papers"]) == 1
    assert payload["papers"][0]["paper_id"] == "paper-1"
    assert len(payload["candidates"]) >= 1
    assert payload["candidates"][0]["name"] == "CulturalVQA"


def test_trend_endpoint_with_monkeypatched_services(monkeypatch) -> None:
    from backend.models.schemas import Author, Paper

    def fake_search_papers(query: str, max_papers: int = 100) -> list[Paper]:
        assert query == "vision language models cultural understanding"
        assert max_papers == 50
        return [
            Paper(
                paper_id="paper-1",
                title="A Trend Paper",
                abstract="Trend abstract",
                year=2024,
                authors=[Author(name="Alice")],
                primary_category="cs.CL",
                categories=["cs.CL", "cs.AI"],
                url="https://example.org/paper",
                open_access_pdf_url="https://example.org/paper.pdf",
            )
        ]

    def fake_analyze_trends(papers: list[Paper], top_k_keywords: int = 20) -> dict:
        assert len(papers) == 1
        assert top_k_keywords == 15
        return {
            "summary": {
                "total_papers": 1,
                "year_min": 2024,
                "year_max": 2024,
                "most_common_primary_category": "cs.CL",
                "paper_count_with_pdf": 1,
            },
            "yearly_counts": [{"year": 2024, "count": 1}],
            "primary_category_counts": [{"category": "cs.CL", "count": 1}],
            "category_counts": [{"category": "cs.CL", "count": 1}, {"category": "cs.AI", "count": 1}],
            "top_keywords": [{"keyword": "vision", "count": 2}],
        }

    monkeypatch.setattr("backend.api.routes.search_papers", fake_search_papers)
    monkeypatch.setattr("backend.api.routes.analyze_trends", fake_analyze_trends)

    response = client.post(
        "/trend",
        json={
            "query": "vision language models cultural understanding",
            "max_papers": 50,
            "top_k_keywords": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "vision language models cultural understanding"
    assert len(payload["papers"]) == 1
    assert payload["summary"]["total_papers"] == 1
    assert payload["yearly_counts"] == [{"year": 2024, "count": 1}]


def test_trend_endpoint_handles_empty_papers(monkeypatch) -> None:
    monkeypatch.setattr("backend.api.routes.search_papers", lambda query, max_papers=100: [])

    response = client.post(
        "/trend",
        json={"query": "empty trend", "max_papers": 10, "top_k_keywords": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["papers"] == []
    assert payload["summary"]["total_papers"] == 0
    assert payload["yearly_counts"] == []


def test_trend_endpoint_retrieval_failure_returns_500(monkeypatch) -> None:
    def fail_search(*args, **kwargs):
        raise RuntimeError("upstream failed")

    monkeypatch.setattr("backend.api.routes.search_papers", fail_search)

    response = client.post(
        "/trend",
        json={"query": "bad", "max_papers": 10, "top_k_keywords": 5},
    )

    assert response.status_code == 500
    assert "Paper retrieval failed" in response.json()["detail"]


def test_trend_endpoint_retrieval_timeout_returns_504(monkeypatch) -> None:
    def fail_search(*args, **kwargs):
        raise RuntimeError("Read timed out")

    monkeypatch.setattr("backend.api.routes.search_papers", fail_search)

    response = client.post(
        "/trend",
        json={"query": "timeout", "max_papers": 10, "top_k_keywords": 5},
    )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


def test_trend_endpoint_rate_limited_returns_503(monkeypatch) -> None:
    def fail_search(*args, **kwargs):
        raise RuntimeError("429 Too Many Requests")

    monkeypatch.setattr("backend.api.routes.search_papers", fail_search)

    response = client.post(
        "/trend",
        json={"query": "rate limit", "max_papers": 10, "top_k_keywords": 5},
    )

    assert response.status_code == 503
    assert "rate-limiting" in response.json()["detail"]
