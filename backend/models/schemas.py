from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    max_papers: int = 10
    extract_from_pdfs: bool = True
    use_model_extractor: bool = False


class Author(BaseModel):
    name: str


class Paper(BaseModel):
    paper_id: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    published_date: Optional[str] = None
    primary_category: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    authors: list[Author] = Field(default_factory=list)
    venue: Optional[str] = None
    url: Optional[str] = None
    open_access_pdf_url: Optional[str] = None
    source: str = "arxiv"


class DatasetCandidate(BaseModel):
    name: str
    source_title: str
    source_paper_id: str
    year: Optional[int] = None
    evidence: str
    evidence_source: str
    paper_url: Optional[str] = None
    pdf_url: Optional[str] = None
    score: float = 0.0
    extraction_method: str = "rule"
    confidence: str = "medium"
    validation_reasons: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    papers: list[Paper]
    candidates: list[DatasetCandidate]
    warnings: list[str] = Field(default_factory=list)


class TrendRequest(BaseModel):
    query: str
    max_papers: int = 100
    top_k_keywords: int = 20


class TrendResponse(BaseModel):
    query: str
    papers: list[Paper]
    summary: dict
    yearly_counts: list[dict]
    primary_category_counts: list[dict]
    category_counts: list[dict]
    top_keywords: list[dict]
    suggested_query_terms: list[str] = Field(default_factory=list)
    manifest_path: Optional[str] = None
