
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apis.interviewer_api import router as interviewer_router

app = FastAPI(title="Agentic Safety Assessment")

# Optional CORS setup for frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration
app.include_router(interviewer_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Agentic Safety Assessment API", "version": "1.0.0"}