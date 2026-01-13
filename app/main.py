import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import config
from app.api.transcript import router as transcript_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting YouTube Transcript Service")
    config.initialize()
    logger.info(f"Cache directory: {config.CACHE_DIR}")
    logger.info(f"Cache enabled: {config.CACHE_ENABLED}")
    logger.info(f"Max concurrent processes: {config.MAX_CONCURRENT_PROCESSES}")

    yield

    # Shutdown
    logger.info("Shutting down YouTube Transcript Service")


# Create FastAPI application
app = FastAPI(
    title="YouTube Transcript Service",
    description="Self-hosted API for fetching YouTube transcripts using yt-dlp",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcript_router, tags=["transcript"])


@app.get("/", tags=["health"])
async def root():
    """Root endpoint - health check"""
    return {
        "service": "YouTube Transcript Service",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "cache_enabled": config.CACHE_ENABLED,
        "cache_dir": str(config.CACHE_DIR)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
