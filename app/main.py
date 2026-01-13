"""
Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import configuration and database
from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import routes
from app.api import openai_routes
from app.api import matching_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print("🚀 Starting up M01N API...")
    #await init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down M01N API...")
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI instance
app = FastAPI(
    title=settings.app_name,
    description="Backend API for M01N project with Supabase",
    version=settings.app_version,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)
app.include_router(openai_routes.router)
app.include_router(matching_routes.router)


# Root endpoint
@app.get("/")
async def read_root():
    """Root endpoint"""
    return {
        "message": "Welcome to M01N API",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "database": "connected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
