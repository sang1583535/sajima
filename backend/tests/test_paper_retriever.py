import pytest

from backend.services.paper_retriever import (
    _extract_arxiv_id,
    _extract_pdf_url,
    _parse_arxiv_response,
    search_papers,
)


SAMPLE_ATOM = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<feed xmlns=\"http://www.w3.org/2005/Atom\">
  <entry>
    <id>http://arxiv.org/abs/2501.12345v2</id>
    <updated>2025-01-20T00:00:00Z</updated>
    <published>2025-01-19T00:00:00Z</published>
    <title>  Datasets for Cultural Understanding in VLMs  </title>
    <summary>  We study datasets for cultural understanding.  </summary>
    <author><name>Jane Doe</name></author>
    <author><name>John Doe</name></author>
    <link href=\"http://arxiv.org/abs/2501.12345v2\" rel=\"alternate\" type=\"text/html\"/>
    <link href=\"http://arxiv.org/pdf/2501.12345v2\" rel=\"related\" type=\"application/pdf\"/>
  </entry>
</feed>
"""


def test_extract_arxiv_id() -> None:
    assert _extract_arxiv_id("http://arxiv.org/abs/2501.12345v2") == "2501.12345"
    assert _extract_arxiv_id("http://arxiv.org/abs/cs.CV/0601001v1") == "cs.CV/0601001"


def test_extract_pdf_url_fallback() -> None:
    class Entry:
        links = []

    assert _extract_pdf_url(Entry(), "2501.12345") == "https://arxiv.org/pdf/2501.12345"


def test_parse_arxiv_response() -> None:
    papers = _parse_arxiv_response(SAMPLE_ATOM)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.paper_id == "2501.12345"
    assert paper.title == "Datasets for Cultural Understanding in VLMs"
    assert paper.abstract == "We study datasets for cultural understanding."
    assert paper.year == 2025
    assert [author.name for author in paper.authors] == ["Jane Doe", "John Doe"]
    assert paper.url == "http://arxiv.org/abs/2501.12345v2"
    assert paper.open_access_pdf_url == "http://arxiv.org/pdf/2501.12345v2"
    assert paper.source == "arxiv"


def test_search_papers_empty_query_raises() -> None:
    with pytest.raises(ValueError):
        search_papers("   ", 5)


def test_search_papers_uses_cached_raw_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.services.paper_retriever.load_cached_papers",
        lambda q, m, provider="default": {"raw": SAMPLE_ATOM},
    )

    papers = search_papers("datasets for cultural understanding in VLMs", 5)
    assert len(papers) == 1
    assert papers[0].paper_id == "2501.12345"
