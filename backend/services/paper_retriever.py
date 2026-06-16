import re
from types import SimpleNamespace
import xml.etree.ElementTree as ET

try:
    import requests
except ImportError:  # pragma: no cover - dependency may be absent in local validation environments
    requests = SimpleNamespace(get=None, RequestException=Exception)

try:
    import feedparser
except ImportError:  # pragma: no cover - dependency may be absent in local validation environments
    feedparser = None

from backend.models.schemas import Author, Paper
from backend.services.cache import load_cached_papers, save_cached_papers

ARXIV_SEARCH_URL = "https://export.arxiv.org/api/query"
PROVIDER_NAME = "arxiv"


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _extract_arxiv_id(entry_id: object) -> str:
    if not isinstance(entry_id, str):
        return ""
    raw = entry_id.strip()
    if "/abs/" in raw:
        raw = raw.split("/abs/", 1)[1]
    else:
        raw = raw.rsplit("/", 1)[-1]
    if not raw:
        return ""
    return re.sub(r"v\d+$", "", raw)


def _parse_year(published: object) -> int | None:
    if not isinstance(published, str) or len(published) < 4:
        return None
    try:
        return int(published[:4])
    except ValueError:
        return None


def _extract_pdf_url(entry: object, paper_id: str) -> str | None:
    links = getattr(entry, "links", None)
    if isinstance(links, list):
        for link in links:
            if isinstance(link, dict) and link.get("type") == "application/pdf":
                href = link.get("href")
                if isinstance(href, str) and href.strip():
                    return href
            href_attr = getattr(link, "href", None)
            type_attr = getattr(link, "type", None)
            if type_attr == "application/pdf" and isinstance(href_attr, str) and href_attr.strip():
                return href_attr

    if paper_id:
        return f"https://arxiv.org/pdf/{paper_id}"
    return None


def _parse_authors(raw_authors: object) -> list[Author]:
    if not isinstance(raw_authors, list):
        return []

    authors: list[Author] = []
    for raw_author in raw_authors:
        name = None
        if isinstance(raw_author, dict):
            name = raw_author.get("name")
        else:
            name = getattr(raw_author, "name", None)

        cleaned_name = _clean_text(name)
        if cleaned_name:
            authors.append(Author(name=cleaned_name))
    return authors


def _extract_primary_category(entry: object) -> str | None:
    raw = getattr(entry, "arxiv_primary_category", None)
    if isinstance(raw, dict):
        term = raw.get("term")
        return _clean_text(term)
    term = getattr(raw, "term", None)
    return _clean_text(term)


def _extract_categories(entry: object) -> list[str]:
    tags = getattr(entry, "tags", None)
    if not isinstance(tags, list):
        return []

    categories: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        term = None
        if isinstance(tag, dict):
            term = tag.get("term")
        else:
            term = getattr(tag, "term", None)

        cleaned_term = _clean_text(term)
        if cleaned_term and cleaned_term not in seen:
            seen.add(cleaned_term)
            categories.append(cleaned_term)
    return categories


def _parse_arxiv_response(response_text: str) -> list[Paper]:
    if feedparser is not None:
        feed = feedparser.parse(response_text)
        entries = getattr(feed, "entries", [])
        if not isinstance(entries, list):
            return []

        papers: list[Paper] = []
        for entry in entries:
            paper_id = _extract_arxiv_id(getattr(entry, "id", None))
            title = _clean_text(getattr(entry, "title", None)) or "Untitled"
            abstract = _clean_text(getattr(entry, "summary", None))
            published_date = _clean_text(getattr(entry, "published", None))
            year = _parse_year(published_date)
            primary_category = _extract_primary_category(entry)
            categories = _extract_categories(entry)
            authors = _parse_authors(getattr(entry, "authors", []))
            url = _clean_text(getattr(entry, "link", None))
            open_access_pdf_url = _extract_pdf_url(entry, paper_id)

            papers.append(
                Paper(
                    paper_id=paper_id,
                    title=title,
                    abstract=abstract,
                    year=year,
                    published_date=published_date,
                    primary_category=primary_category,
                    categories=categories,
                    authors=authors,
                    venue="arXiv",
                    url=url,
                    open_access_pdf_url=open_access_pdf_url,
                    source="arxiv",
                )
            )
        return papers

    papers: list[Paper] = []
    try:
        root = ET.fromstring(response_text)
    except ET.ParseError:
        return []

    namespace = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    for entry in root.findall("atom:entry", namespace):
        entry_id = entry.findtext("atom:id", default="", namespaces=namespace)
        title = _clean_text(entry.findtext("atom:title", default="", namespaces=namespace)) or "Untitled"
        abstract = _clean_text(entry.findtext("atom:summary", default="", namespaces=namespace))
        published_date = _clean_text(entry.findtext("atom:published", default="", namespaces=namespace))
        year = _parse_year(published_date)
        primary_category_element = entry.find("arxiv:primary_category", namespace)
        primary_category = _clean_text(
            primary_category_element.attrib.get("term") if primary_category_element is not None else None
        )
        categories: list[str] = []
        seen_categories: set[str] = set()
        for category_element in entry.findall("atom:category", namespace):
            term = _clean_text(category_element.attrib.get("term"))
            if term and term not in seen_categories:
                seen_categories.add(term)
                categories.append(term)

        authors = []
        for author in entry.findall("atom:author", namespace):
            name = _clean_text(author.findtext("atom:name", default="", namespaces=namespace))
            if name:
                authors.append(Author(name=name))

        url = None
        open_access_pdf_url = None
        for link in entry.findall("atom:link", namespace):
            href = link.attrib.get("href")
            if not url and href and link.attrib.get("rel") == "alternate":
                url = href
            if not open_access_pdf_url and href and link.attrib.get("type") == "application/pdf":
                open_access_pdf_url = href

        paper_id = _extract_arxiv_id(entry_id)
        if not open_access_pdf_url and paper_id:
            open_access_pdf_url = f"https://arxiv.org/pdf/{paper_id}"

        papers.append(
            Paper(
                paper_id=paper_id,
                title=title,
                abstract=abstract,
                year=year,
                published_date=published_date,
                primary_category=primary_category,
                categories=categories,
                authors=authors,
                venue="arXiv",
                url=url,
                open_access_pdf_url=open_access_pdf_url,
                source="arxiv",
            )
        )
    return papers


def search_papers(query: str, max_papers: int = 10) -> list[Paper]:
    """Search papers from arXiv and return normalized metadata."""
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Query must not be empty.")

    cached = load_cached_papers(cleaned_query, max_papers, provider=PROVIDER_NAME)
    if isinstance(cached, dict):
        cached_raw = cached.get("raw")
        if isinstance(cached_raw, str):
            try:
                return _parse_arxiv_response(cached_raw)
            except Exception:
                return []

    params = {
        "search_query": f"all:{cleaned_query}",
        "start": 0,
        "max_results": max_papers,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        if requests.get is None:
            raise RuntimeError("arXiv request failed: requests is not installed.")
        response = requests.get(ARXIV_SEARCH_URL, params=params, timeout=15)
        response.raise_for_status()
        response_text = response.text
    except requests.RequestException as exc:
        raise RuntimeError(f"arXiv request failed: {exc}") from exc

    save_cached_papers(cleaned_query, max_papers, {"raw": response_text}, provider=PROVIDER_NAME)

    try:
        return _parse_arxiv_response(response_text)
    except Exception:
        return []
