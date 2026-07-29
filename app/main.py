# fastapi
from fastapi import FastAPI

# app
from app.api.v1.endpoints import auth
from app.models.user import Base
from app.api.deps import engine



Base.metadata.create_all(bind=engine)

app = FastAPI(title="Aiuto V2 API", version="1.0.0")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

@app.get("/health")
def health_check():
    return {"status": "ok"}