from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"
SEARCH_TIMEOUT_SECONDS = 90
TREND_TIMEOUT_SECONDS = 120

st.set_page_config(page_title="Dataset Finder", page_icon="🔎", layout="wide")


if "search_result" not in st.session_state:
    st.session_state.search_result = None
if "search_error" not in st.session_state:
    st.session_state.search_error = None
if "use_model_extractor" not in st.session_state:
    st.session_state.use_model_extractor = False
if "trend_result" not in st.session_state:
    st.session_state.trend_result = None
if "trend_error" not in st.session_state:
    st.session_state.trend_error = None


def _fetch_search_results(query: str, max_papers: int, extract_from_pdfs: bool, use_model_extractor: bool) -> dict:
    payload = {
        "query": query,
        "max_papers": int(max_papers),
        "extract_from_pdfs": extract_from_pdfs,
        "use_model_extractor": use_model_extractor,
    }
    response = requests.post(
        f"{BACKEND_URL}/search",
        json=payload,
        timeout=SEARCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _fetch_trend_results(query: str, max_papers: int, top_k_keywords: int) -> dict:
    payload = {
        "query": query,
        "max_papers": int(max_papers),
        "top_k_keywords": int(top_k_keywords),
    }
    response = requests.post(
        f"{BACKEND_URL}/trend",
        json=payload,
        timeout=TREND_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _show_dataset_finder_results(result: dict) -> None:
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


def _show_trend_results(result: dict) -> None:
    papers = result.get("papers", [])
    summary = result.get("summary", {})
    yearly_counts = result.get("yearly_counts", [])
    primary_category_counts = result.get("primary_category_counts", [])
    category_counts = result.get("category_counts", [])
    top_keywords = result.get("top_keywords", [])
    suggested_query_terms = result.get("suggested_query_terms", [])

    if not papers:
        st.info("No papers were found for this topic.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total papers", summary.get("total_papers", 0))

    year_min = summary.get("year_min")
    year_max = summary.get("year_max")
    year_range = "N/A" if year_min is None or year_max is None else f"{year_min} - {year_max}"
    col2.metric("Year range", year_range)
    col3.metric("Top primary category", summary.get("most_common_primary_category") or "N/A")
    col4.metric("Papers with PDF", summary.get("paper_count_with_pdf", 0))

    st.subheader("Yearly paper count")
    yearly_df = pd.DataFrame(yearly_counts)
    if yearly_counts:
        yearly_df = yearly_df.sort_values("year")
        st.line_chart(yearly_df.set_index("year")["count"])
    else:
        st.info("No yearly count data available.")

    st.subheader("Primary category distribution")
    primary_df = pd.DataFrame(primary_category_counts)
    if primary_category_counts:
        st.bar_chart(primary_df.set_index("category")["count"])
    else:
        st.info("No primary category data available.")

    st.subheader("All category counts")
    category_df = pd.DataFrame(category_counts)
    if category_counts:
        st.bar_chart(category_df.set_index("category")["count"])
    else:
        st.info("No category count data available.")

    st.subheader("Top keywords")
    keyword_df = pd.DataFrame(top_keywords)
    if top_keywords:
        st.bar_chart(keyword_df.set_index("keyword")["count"])
    else:
        st.info("No keyword data available.")

    st.subheader("Query expansion suggestions")
    if suggested_query_terms:
        st.caption("Try adding these terms to refine or expand your next trend query.")
        st.write(", ".join(suggested_query_terms))
    else:
        st.info("No query expansion suggestions available.")

    st.subheader("Retrieved papers")
    table_rows: list[dict] = []
    for paper in papers:
        categories = paper.get("categories", [])
        table_rows.append(
            {
                "title": paper.get("title"),
                "year": paper.get("year"),
                "primary_category": paper.get("primary_category"),
                "categories": ", ".join(categories) if isinstance(categories, list) else "",
                "url": paper.get("url"),
                "open_access_pdf_url": paper.get("open_access_pdf_url"),
            }
        )
    papers_df = pd.DataFrame(table_rows)
    st.dataframe(papers_df, use_container_width=True)

    with st.expander("Export results"):
        if not papers_df.empty:
            st.download_button(
                "Download papers CSV",
                data=papers_df.to_csv(index=False).encode("utf-8"),
                file_name="papers.csv",
                mime="text/csv",
            )
        if not yearly_df.empty:
            st.download_button(
                "Download yearly counts CSV",
                data=yearly_df.to_csv(index=False).encode("utf-8"),
                file_name="yearly_counts.csv",
                mime="text/csv",
            )
        if not primary_df.empty:
            st.download_button(
                "Download primary category counts CSV",
                data=primary_df.to_csv(index=False).encode("utf-8"),
                file_name="primary_category_counts.csv",
                mime="text/csv",
            )
        if not category_df.empty:
            st.download_button(
                "Download category counts CSV",
                data=category_df.to_csv(index=False).encode("utf-8"),
                file_name="category_counts.csv",
                mime="text/csv",
            )
        if not keyword_df.empty:
            st.download_button(
                "Download top keywords CSV",
                data=keyword_df.to_csv(index=False).encode("utf-8"),
                file_name="top_keywords.csv",
                mime="text/csv",
            )


st.title("Dataset Finder")

tab1, tab2 = st.tabs(["Dataset Finder", "ArxivTrendIR"])

with tab1:
    st.subheader("Dataset Finder")
    with st.form("dataset_finder_form", clear_on_submit=False):
        query = st.text_input("Query", placeholder="Search for papers or datasets...")
        max_papers = st.number_input("Max papers", min_value=1, max_value=100, value=10, step=1)
        extract_from_pdfs = st.checkbox("Extract from open-access PDFs", value=True)
        use_model_extractor = st.checkbox("Use optional GLiNER extractor", value=False)
        st.caption("The GLiNER extractor may be slower and may download a pretrained model on first use.")
        submitted = st.form_submit_button("Search")

        if submitted:
            if not query.strip():
                st.session_state.search_error = "Please enter a query."
                st.session_state.search_result = None
            else:
                try:
                    with st.spinner("Searching..."):
                        st.session_state.search_result = _fetch_search_results(
                            query,
                            int(max_papers),
                            extract_from_pdfs,
                            use_model_extractor,
                        )
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

    if st.session_state.search_error:
        st.error(st.session_state.search_error)
    if st.session_state.search_result:
        _show_dataset_finder_results(st.session_state.search_result)

with tab2:
    st.subheader("ArxivTrendIR: Topic-based arXiv Research Trend Explorer")
    with st.form("trend_form", clear_on_submit=False):
        trend_query = st.text_input("Topic / Query", placeholder="e.g. vision language models cultural understanding")
        trend_max_papers = st.slider("Max papers", min_value=10, max_value=200, value=100, step=10)
        trend_top_k_keywords = st.slider("Top keywords", min_value=5, max_value=30, value=15, step=1)
        trend_submitted = st.form_submit_button("Analyze Topic")

        if trend_submitted:
            if not trend_query.strip():
                st.session_state.trend_error = "Please enter a topic query."
                st.session_state.trend_result = None
            else:
                try:
                    with st.spinner("Analyzing trend..."):
                        st.session_state.trend_result = _fetch_trend_results(
                            trend_query,
                            trend_max_papers,
                            trend_top_k_keywords,
                        )
                    st.session_state.trend_error = None
                except requests.ConnectionError:
                    st.session_state.trend_result = None
                    st.session_state.trend_error = "Backend is not running. Start the FastAPI server and try again."
                except requests.Timeout:
                    st.session_state.trend_result = None
                    st.session_state.trend_error = "Trend analysis timed out. Try reducing max papers."
                except requests.RequestException as exc:
                    st.session_state.trend_result = None
                    st.session_state.trend_error = f"Trend request failed: {exc}"

    if st.session_state.trend_error:
        st.error(st.session_state.trend_error)
    if st.session_state.trend_result:
        _show_trend_results(st.session_state.trend_result)
