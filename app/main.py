# fastapi
from fastapi import FastAPI

# app
from app.api.v1.endpoints import auth, ai



app = FastAPI(title="Aiuto V2 API", version="1.0.0")

app.include_router(
    auth.router,
    prefix="/api/v1/auth", 
    tags=["Authentication"])

app.include_router(
    ai.router,
    prefix="/api/v1/ai",
    tags=["AI Jobs"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}