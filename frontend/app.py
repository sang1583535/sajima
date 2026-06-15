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
            st.json(response.json())
        except requests.RequestException as exc:
            st.error(f"Failed to reach backend: {exc}")
