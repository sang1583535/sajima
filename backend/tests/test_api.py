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
