from fastapi import APIRouter, HTTPException

from backend.models.schemas import SearchRequest, SearchResponse
from backend.services.paper_retriever import search_papers

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    try:
        papers = search_papers(request.query, request.max_papers)
        return SearchResponse(query=request.query, papers=papers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        detail = str(exc)
        if "429" in detail:
            raise HTTPException(
                status_code=503,
                detail="Search provider is rate-limiting requests right now. Please retry in a moment.",
            ) from exc
        raise HTTPException(status_code=502, detail=f"Search provider error: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc
