import json
from datetime import date
from pathlib import Path

from backend.services import manifest


def test_safe_query_folder_name() -> None:
    query = "Vision Language Models: Cultural Understanding!!! 2025"
    slug = manifest.safe_query_folder_name(query)

    assert slug == "vision-language-models-cultural-understanding-2025"
    assert len(slug) <= 80


def test_save_trend_manifest_creates_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(manifest, "PROCESSED_DIR", tmp_path / "data" / "processed")

    response_data = {
        "query": "vision language models",
        "papers": [{"paper_id": "p1", "title": "Paper"}],
        "summary": {"total_papers": 1},
        "yearly_counts": [{"year": 2024, "count": 1}],
        "primary_category_counts": [{"category": "cs.CL", "count": 1}],
        "category_counts": [{"category": "cs.CL", "count": 1}],
        "top_keywords": [{"keyword": "vision", "count": 1}],
    }

    manifest_path = manifest.save_trend_manifest("Vision Language Models", response_data)

    assert manifest_path
    path = Path(manifest_path)
    assert path.exists()
    assert path.name == "manifest.json"
    assert path.parent.name == "vision-language-models"
    assert path.parent.parent.name == date.today().isoformat()

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["query"] == "vision language models"
    assert loaded["summary"]["total_papers"] == 1
