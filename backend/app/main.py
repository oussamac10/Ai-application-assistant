from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router

app = FastAPI(
    title="AI Form Assistant API",
    description="Multilingual AI form assistant API",
    version="1.0.0",
)

# Set up CORS middleware - in dev, allow localhost frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production, but * is simple for dev foundation
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
