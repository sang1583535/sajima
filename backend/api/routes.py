from fastapi import APIRouter

from backend.models.schemas import SearchRequest, SearchResponse

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(query=request.query, results=[])
