"""
api/main.py
FastAPI app — deployed on Render, fetches jobs from Neon Postgres.
Serves JSON consumed by the GitHub Pages static UI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(
    title="DevOps Jobs Board API",
    description="Job listings for DevOps, Cloud, SRE, and MLOps roles in Ireland",
    version="1.0.0",
)

# Allow GitHub Pages origin (and localhost for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your Pages URL in production
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
