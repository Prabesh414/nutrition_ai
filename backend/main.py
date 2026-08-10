from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI-Based Personalized Diet Recommendation & Nutrition Management API",
    description="Backend API services for user profile calculations, diet recommendations, meal tracking, and chatbot assistance.",
    version="1.0.0"
)

# Configure CORS for React frontend (on npm/bun dev port, typically 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Nutrition AI API",
        "docs_url": "/docs",
        "status": "healthy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
