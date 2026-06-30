from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_upload import router as upload_router
from app.api.routes_analysis import router as analysis_router

app = FastAPI(
    title="Drum Groove Decomposition Tool",
    description="Backend API for uploading pre-separated drum stems and analyzing rhythmic events.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(analysis_router, prefix="/api", tags=["analysis"])


@app.get("/")
async def root():
    return {
        "message": "Drum Groove Decomposition Tool API is running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
    }
