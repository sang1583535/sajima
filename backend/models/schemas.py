from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    max_papers: int = 10


class Author(BaseModel):
    name: str


class Paper(BaseModel):
    paper_id: str
    title: str
    abstract: str | None = None
    year: int | None = None
    authors: list[Author] = Field(default_factory=list)
    venue: str | None = None
    url: str | None = None
    open_access_pdf_url: str | None = None
    source: str = "arxiv"


class DatasetCandidate(BaseModel):
    name: str
    source_title: str
    evidence: str
    url: str | None = None
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    papers: list[Paper]
