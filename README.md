# Dataset Finder

Minimal starter scaffold for a FastAPI backend and Streamlit frontend.

## Setup

1. Create and activate a Conda environment:
   - `conda create -n dataset-finder python=3.11 -y`
   - `conda activate dataset-finder`
2. Install dependencies:
   - `pip install -r requirements.txt`

## Run

1. Run backend:
   - `./scripts/run_backend.sh`
2. Run frontend:
   - `./scripts/run_frontend.sh`

Or run both:

- `./scripts/run_all.sh`

## Health Check

With backend running:

- `curl http://localhost:8000/health`

Expected response:

```json
{"status":"ok"}
```
