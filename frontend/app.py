from __future__ import annotations

import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"
SEARCH_TIMEOUT_SECONDS = 90

st.set_page_config(page_title="Dataset Finder", page_icon="🔎", layout="wide")


def _format_authors(authors: list[dict]) -> str:
    names = [author.get("name", "") for author in authors if isinstance(author, dict)]
    return ", ".join(name for name in names if name) or "N/A"


def _format_abstract_preview(abstract: str | None, limit: int = 300) -> str:
    if not abstract:
        return "N/A"
    return abstract[:limit] + ("..." if len(abstract) > limit else "")


def _fetch_results(query: str, max_papers: int, extract_from_pdfs: bool) -> dict:
    payload = {
        "query": query,
        "max_papers": int(max_papers),
        "extract_from_pdfs": extract_from_pdfs,
        "use_model_extractor": st.session_state.use_model_extractor,
    }
    response = requests.post(
        f"{BACKEND_URL}/search",
        json=payload,
        timeout=SEARCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


if "page" not in st.session_state:
    st.session_state.page = "Search"
if "search_result" not in st.session_state:
    st.session_state.search_result = None
if "search_error" not in st.session_state:
    st.session_state.search_error = None
if "use_model_extractor" not in st.session_state:
    st.session_state.use_model_extractor = False

st.sidebar.title("Dataset Finder")
st.sidebar.caption("Search papers from the sidebar, then review results on the main page.")
view = st.sidebar.radio("Navigation", ["Search", "About"], index=0 if st.session_state.page == "Search" else 1)
st.session_state.page = view

with st.sidebar.form("search_form", clear_on_submit=False):
    query = st.text_input("Query", placeholder="Search for papers or datasets...")
    max_papers = st.number_input("Max papers", min_value=1, max_value=100, value=10, step=1)
    extract_from_pdfs = st.checkbox("Extract from open-access PDFs", value=True)
    use_model_extractor = st.checkbox("Use optional GLiNER extractor", value=False)
    st.caption("The GLiNER extractor may be slower and may download a pretrained model on first use.")
    submitted = st.form_submit_button("Search")

    st.session_state.use_model_extractor = use_model_extractor

    if submitted:
        if not query.strip():
            st.session_state.search_error = "Please enter a query."
            st.session_state.search_result = None
        else:
            try:
                with st.spinner("Searching..."):
                    st.session_state.search_result = _fetch_results(query, max_papers, extract_from_pdfs)
                st.session_state.search_error = None
            except requests.ConnectionError:
                st.session_state.search_result = None
                st.session_state.search_error = "Backend is not running. Start the FastAPI server and try again."
            except requests.Timeout:
                st.session_state.search_result = None
                st.session_state.search_error = (
                    "The search took too long. Try lowering max_papers or disabling PDF extraction."
                )
            except requests.RequestException as exc:
                st.session_state.search_result = None
                st.session_state.search_error = f"Search request failed: {exc}"


if st.session_state.page == "About":
    st.title("About")
    st.write("Dataset Finder helps search papers and surface dataset or benchmark candidates.")
    st.write("Use the sidebar to run a search, then review the results directly on the Search page.")
    st.write("The MVP focuses on fast paper search, PDF text extraction, rule-based candidate extraction, and ranking.")
else:
    st.title("Dataset Finder")
    st.write("Use the sidebar to search for papers and review extracted candidates in cards below.")
    st.write("The main page stays simple and updates in place after each search.")


if st.session_state.search_error:
    st.error(st.session_state.search_error)


if st.session_state.page == "Search" and st.session_state.search_result:
    result = st.session_state.search_result
    papers = result.get("papers", [])
    candidates = result.get("candidates", [])

    st.subheader("Extracted candidates")
    if not candidates:
        st.info(
            "No dataset or benchmark candidates were found. Try increasing max_papers or disabling PDF extraction."
        )
    else:
        for index, candidate in enumerate(candidates, start=1):
            name = candidate.get("name", "Unnamed candidate")
            score = candidate.get("score", 0.0)
            source_title = candidate.get("source_title", "N/A")
            year = candidate.get("year")
            evidence_source = candidate.get("evidence_source", "N/A")
            evidence = candidate.get("evidence", "N/A")
            extraction_method = candidate.get("extraction_method", "rule")
            confidence = candidate.get("confidence", "medium")
            validation_reasons = candidate.get("validation_reasons", [])
            paper_url = candidate.get("paper_url")
            pdf_url = candidate.get("pdf_url")

            with st.container(border=True):
                st.markdown(f"**{index}. {name}**")
                st.caption(f"Score: {score:.2f}")
                st.write(f"Source paper: {source_title}")
                st.write(f"Year: {year if year is not None else 'N/A'}")
                st.write(f"Extraction method: {extraction_method}")
                st.write(f"Confidence: {confidence}")
                st.write(f"Evidence source: {evidence_source}")
                if validation_reasons:
                    st.write(f"Validation reasons: {', '.join(validation_reasons)}")
                st.write(evidence)
                if paper_url:
                    st.write(f"Paper URL: {paper_url}")
                if pdf_url:
                    st.write(f"PDF URL: {pdf_url}")

    warnings = result.get("warnings", [])
    for warning in warnings:
        st.warning(warning)

    st.subheader("Retrieved papers")
    if not papers:
        st.info("No papers found for this query.")
    else:
        st.success(f"Found {len(papers)} paper(s).")
        for index, paper in enumerate(papers, start=1):
            title = paper.get("title") or "Untitled"
            year = paper.get("year")
            venue = paper.get("venue")
            source = paper.get("source") or "unknown"
            abstract = paper.get("abstract")
            authors = paper.get("authors", [])
            paper_url = paper.get("url")
            pdf_url = paper.get("open_access_pdf_url")

            author_names = ", ".join(
                author.get("name", "") for author in authors if isinstance(author, dict)
            ).strip(", ")

            with st.expander(f"{index}. {title}", expanded=False):
                st.write(f"Year: {year if year is not None else 'N/A'}")
                st.write(f"Authors: {author_names or 'N/A'}")
                st.write(f"Venue: {venue or 'N/A'}")
                st.write(f"Source: {source}")
                st.write(
                    f"Abstract: {(abstract[:400] + '...') if isinstance(abstract, str) and len(abstract) > 400 else (abstract or 'N/A')}"
                )
                if paper_url:
                    st.markdown(f"Paper URL: [{paper_url}]({paper_url})")
                if pdf_url:
                    st.markdown(f"PDF URL: [{pdf_url}]({pdf_url})")
