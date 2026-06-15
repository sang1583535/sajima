from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    max_papers: int = 10


class DatasetCandidate(BaseModel):
    name: str
    source_title: str
    evidence: str
    url: str | None = None
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    results: list[DatasetCandidate]
