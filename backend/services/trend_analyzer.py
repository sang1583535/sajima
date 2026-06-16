from __future__ import annotations

import re
from collections import Counter

from backend.models.schemas import Paper

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "such",
    "that",
    "the",
    "their",
    "this",
    "to",
    "we",
    "with",
    "our",
    "using",
    "use",
    "used",
    "via",
    "towards",
    "toward",
    "can",
    "may",
    "new",
    "based",
    "approach",
    "approaches",
    "method",
    "methods",
    "model",
    "models",
    "paper",
    "study",
    "results",
}


def compute_yearly_counts(papers: list[Paper]) -> list[dict]:
    counter: Counter[int] = Counter()
    for paper in papers:
        if paper.year is not None:
            counter[paper.year] += 1

    return [
        {"year": year, "count": count}
        for year, count in sorted(counter.items(), key=lambda item: item[0])
    ]


def compute_primary_category_counts(papers: list[Paper]) -> list[dict]:
    counter: Counter[str] = Counter()
    for paper in papers:
        if paper.primary_category:
            counter[paper.primary_category] += 1

    return [
        {"category": category, "count": count}
        for category, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def compute_all_category_counts(papers: list[Paper]) -> list[dict]:
    counter: Counter[str] = Counter()
    for paper in papers:
        for category in paper.categories:
            if category:
                counter[category] += 1

    return [
        {"category": category, "count": count}
        for category, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _tokenize_text(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())


def extract_top_keywords(papers: list[Paper], top_k: int = 20) -> list[dict]:
    counter: Counter[str] = Counter()

    for paper in papers:
        parts = [paper.title]
        if paper.abstract:
            parts.append(paper.abstract)
        combined = " ".join(parts)

        for token in _tokenize_text(combined):
            if len(token) < 3:
                continue
            if token in STOPWORDS:
                continue
            counter[token] += 1

    return [
        {"keyword": keyword, "count": count}
        for keyword, count in counter.most_common(max(top_k, 0))
    ]


def suggest_query_terms(top_keywords: list[dict], max_terms: int = 8) -> list[str]:
    suggestions: list[str] = []
    seen: set[str] = set()

    for item in top_keywords:
        keyword = item.get("keyword") if isinstance(item, dict) else None
        if not isinstance(keyword, str):
            continue
        cleaned = keyword.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        suggestions.append(cleaned)
        if len(suggestions) >= max(max_terms, 0):
            break

    return suggestions


def build_trend_summary(papers: list[Paper]) -> dict:
    years = [paper.year for paper in papers if paper.year is not None]
    primary_counts = compute_primary_category_counts(papers)

    return {
        "total_papers": len(papers),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "most_common_primary_category": primary_counts[0]["category"] if primary_counts else None,
        "paper_count_with_pdf": sum(1 for paper in papers if paper.open_access_pdf_url),
    }


def analyze_trends(papers: list[Paper], top_k_keywords: int = 20) -> dict:
    top_keywords = extract_top_keywords(papers, top_k=top_k_keywords)
    return {
        "summary": build_trend_summary(papers),
        "yearly_counts": compute_yearly_counts(papers),
        "primary_category_counts": compute_primary_category_counts(papers),
        "category_counts": compute_all_category_counts(papers),
        "top_keywords": top_keywords,
        "suggested_query_terms": suggest_query_terms(top_keywords, max_terms=8),
    }
