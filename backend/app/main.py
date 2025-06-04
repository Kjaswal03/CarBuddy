from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import users, cars, diagnostics, maintenance
from app.agents.maintenance_agent import MaintenanceAgent
from app.services.openai_service import OpenAIService
import asyncio

app = FastAPI(title="CarBuddy AI Agent", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
openai_service = OpenAIService()
maintenance_agent = MaintenanceAgent(openai_service)

# Include routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(cars.router, prefix="/api/v1/cars", tags=["cars"])
app.include_router(diagnostics.router, prefix="/api/v1/diagnostics", tags=["diagnostics"])
app.include_router(maintenance.router, prefix="/api/v1/maintenance", tags=["maintenance"])

@app.get("/")
async def root():
    return {"message": "CarBuddy AI Agent API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)