# Dataset Finder

## Motivation
Dataset and benchmark names are often hidden inside paper content, making them harder to find through ordinary paper search.

## ArxivTrendIR: Topic-based arXiv Exploration
ArxivTrendIR retrieves papers from arXiv for a user topic and computes metadata-based research trend statistics.

## Features
- Search papers from arXiv or other scholarly providers
- Download open-access PDFs when available
- Extract text using PyMuPDF
- Extract dataset / benchmark candidates using rule-based patterns
- Optionally use a pretrained GLiNER extractor for additional candidate suggestions
- Show evidence snippets for verification
- Topic-based arXiv retrieval for trend analysis
- Yearly paper count visualization
- Primary category distribution
- All category distribution
- Top keyword extraction
- Paper table view
- Manifest export for reproducibility
- CSV export from ArxivTrendIR results
- Optional extension to dataset/benchmark extraction

## Architecture
- FastAPI backend
- Streamlit frontend
- arXiv API retrieval
- Local cache under `.cache/`
- Optional model cache under `.models/`
- Processed manifests under `data/processed/`

## IR Pipeline
User query
-> arXiv API retrieval
-> metadata normalization
-> statistics computation
-> visualization
-> manifest export

## Trend Manifests
ArxivTrendIR runs export a reproducible JSON manifest under `data/processed/`.

- Path format: `data/processed/YYYY-MM-DD/<safe-query-folder>/manifest.json`
- Each manifest contains the query, retrieved papers, and computed trend statistics.
- These files are generated artifacts from each trend run.

## Limitations
The system extracts candidates, not guaranteed ground truth. PDF parsing and rule-based extraction can be noisy, so each candidate is shown with evidence snippets.

## Optional GLiNER Extractor

The default extractor is rule-based. A pretrained GLiNER extractor is available as an optional enhancement from the UI.

- No training is performed.
- The pretrained model is downloaded to `.models/` on first use.
- The model is applied only to relevant chunks, so it remains optional and slower than the rule-based path.
- If GLiNER is unavailable, the app falls back to rule-based extraction.

Optional install:

```bash
pip install gliner torch
```

`.models/` is ignored by Git.

## How to Run
Backend:

```bash
bash scripts/run_backend.sh
```

Frontend:

```bash
bash scripts/run_frontend.sh
```

## How to Test

```bash
pytest
```