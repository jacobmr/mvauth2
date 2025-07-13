from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn
import os
from dotenv import load_dotenv

from routes import auth, users, validation, community, roles, landing, mobile
from utils.database import init_db
from utils.config import settings

load_dotenv()

app = FastAPI(
    title="MVAuth2 Service",
    description="Centralized authentication service for multiple applications, starting with ARC project",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(validation.router, prefix="/validate", tags=["validation"])
app.include_router(community.router, prefix="/community", tags=["community"])
app.include_router(roles.router, prefix="/roles", tags=["role-management"])
app.include_router(landing.router, prefix="/api", tags=["applications"])  # API endpoints for applications
app.include_router(mobile.router, prefix="/mobile", tags=["mobile-app"])  # QR Guardian mobile app endpoints

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/api")
async def api_status():
    return {"service": "MVAuth2 Service", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)