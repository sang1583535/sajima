from fastapi import FastAPI

from backend.api.routes import router as api_router

app = FastAPI(title="Dataset Finder API")
app.include_router(api_router)
