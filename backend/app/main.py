from fastapi import FastAPI

app = FastAPI(
    title="NyayaAI API",
    description="Indian Legal & Civic Assistance Platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "nyaya-ai",
    }