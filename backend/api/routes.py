from fastapi import APIRouter, HTTPException

from backend.models.schemas import (
    DatasetCandidate,
    Paper,
    SearchRequest,
    SearchResponse,
    TrendRequest,
    TrendResponse,
)
from backend.services.candidate_merger import merge_candidates
from backend.services.dataset_extractor import extract_dataset_candidates_from_text
from backend.services.pdf_downloader import download_pdf
from backend.services.pdf_parser import extract_text_from_pdf
from backend.services.model_extractor import (
    extract_candidates_with_gliner,
    get_gliner_model,
)
from backend.services.manifest import save_trend_manifest
from backend.services.ranker import rank_candidates
from backend.services.paper_retriever import search_papers
from backend.services.trend_analyzer import analyze_trends

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    try:
        papers = search_papers(request.query, request.max_papers)
        candidates, warnings = _build_candidates(
            papers,
            request.extract_from_pdfs,
            request.use_model_extractor,
        )
        ranked_candidates = rank_candidates(request.query, candidates)
        return SearchResponse(query=request.query, papers=papers, candidates=ranked_candidates, warnings=warnings)
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


@router.post("/trend", response_model=TrendResponse)
def analyze_topic_trend(request: TrendRequest) -> TrendResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    try:
        papers = search_papers(query=request.query, max_papers=request.max_papers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        detail = str(exc)
        detail_lower = detail.lower()
        if "429" in detail:
            raise HTTPException(
                status_code=503,
                detail="Search provider is rate-limiting requests right now. Please retry in a moment.",
            ) from exc
        if "timed out" in detail_lower or "timeout" in detail_lower:
            raise HTTPException(
                status_code=504,
                detail="Search provider timed out while retrieving papers. Please retry or reduce max_papers.",
            ) from exc
        raise HTTPException(status_code=502, detail=f"Search provider error: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Paper retrieval failed: {exc}") from exc

    try:
        trend = analyze_trends(papers, top_k_keywords=request.top_k_keywords)
        response = TrendResponse(
            query=request.query,
            papers=papers,
            summary=trend.get("summary", {}),
            yearly_counts=trend.get("yearly_counts", []),
            primary_category_counts=trend.get("primary_category_counts", []),
            category_counts=trend.get("category_counts", []),
            top_keywords=trend.get("top_keywords", []),
            suggested_query_terms=trend.get("suggested_query_terms", []),
        )
        manifest_path = save_trend_manifest(request.query, response.model_dump())
        return response.model_copy(update={"manifest_path": manifest_path or None})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {exc}") from exc


def _metadata_text(paper: Paper) -> str:
    parts = [paper.title]
    if paper.abstract:
        parts.append(paper.abstract)
    return " ".join(parts)


def _build_candidates(
    papers: list[Paper],
    extract_from_pdfs: bool,
    use_model_extractor: bool,
) -> tuple[list[DatasetCandidate], list[str]]:
    rule_candidates: list[DatasetCandidate] = []
    model_candidates: list[DatasetCandidate] = []
    warnings: list[str] = []

    model_available = False
    if use_model_extractor:
        model_available = get_gliner_model() is not None
        if not model_available:
            warnings.append("GLiNER extractor is unavailable or could not be loaded; using the rule-based extractor only.")

    for paper in papers:
        metadata_text = _metadata_text(paper)
        rule_candidates.extend(
            extract_dataset_candidates_from_text(metadata_text, paper, evidence_source="metadata")
        )

        pdf_text = None
        if extract_from_pdfs and paper.open_access_pdf_url:
            pdf_path = download_pdf(paper.open_access_pdf_url, paper.paper_id)
            if pdf_path:
                pdf_text = extract_text_from_pdf(pdf_path)

        if pdf_text:
            rule_candidates.extend(
                extract_dataset_candidates_from_text(pdf_text, paper, evidence_source="pdf")
            )

        if use_model_extractor and model_available:
            model_source_text = pdf_text if pdf_text else metadata_text
            evidence_source = "gliner_pdf" if pdf_text else "gliner_metadata"
            try:
                model_candidates.extend(
                    extract_candidates_with_gliner(
                        model_source_text,
                        paper,
                        evidence_source=evidence_source,
                    )
                )
            except Exception:
                continue

    return merge_candidates(rule_candidates, model_candidates), warnings
