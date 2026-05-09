from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="OptiPrice AI — Core API",
    version="0.1.0",
    description="Multi-channel dynamic pricing & listing agent backend.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "optiprice-backend"}
