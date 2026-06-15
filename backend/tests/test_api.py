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

    response = client.post(
        "/search",
        json={"query": "vision language datasets", "max_papers": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "vision language datasets"
    assert len(payload["papers"]) == 1
    assert payload["papers"][0]["paper_id"] == "paper-1"
