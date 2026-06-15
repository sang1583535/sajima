import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"

st.title("Dataset Finder")

query = st.text_input("Query", placeholder="Search for papers or datasets...")
max_papers = st.number_input("Max papers", min_value=1, max_value=100, value=10, step=1)

if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a query.")
    else:
        payload = {"query": query, "max_papers": int(max_papers)}
        try:
            response = requests.post(f"{BACKEND_URL}/search", json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            papers = data.get("papers", [])

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

                    st.markdown(f"### {index}. {title}")
                    st.write(f"Year: {year if year is not None else 'N/A'}")
                    st.write(f"Authors: {author_names or 'N/A'}")
                    st.write(f"Venue: {venue or 'N/A'}")
                    st.write(f"Source: {source}")
                    st.write(
                        f"Abstract: {(abstract[:400] + '...') if isinstance(abstract, str) and len(abstract) > 400 else (abstract or 'N/A')}"
                    )
                    if paper_url:
                        st.markdown(f"arXiv URL: [{paper_url}]({paper_url})")
                    if pdf_url:
                        st.markdown(f"PDF URL: [{pdf_url}]({pdf_url})")
                    st.divider()
        except requests.ConnectionError:
            st.error("Backend is not running. Start the FastAPI server and try again.")
        except requests.RequestException as exc:
            st.error(f"Search request failed: {exc}")
