from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import conflicts, deliverable, extract, pipeline, piles, review, rules, upload
from app.config import settings  # noqa: F401 - imported to load/validate config at startup

app = FastAPI(title="Doctask Document Pile API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(piles.router)
app.include_router(upload.router)
app.include_router(extract.router)
app.include_router(conflicts.router)
app.include_router(pipeline.router)
app.include_router(deliverable.router)
app.include_router(rules.router)
app.include_router(review.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
