import logging
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import config
from app.api.transcript import router as transcript_router

# Windows-specific fix for asyncio subprocess support
if sys.platform == "win32":
    # Set the event loop policy to use WindowsProactorEventLoopPolicy
    # This enables subprocess support on Windows with asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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

# Add CORS middleware - restricted for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,  # Configured via environment variable
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Only needed methods
    allow_headers=["Content-Type", "Accept"],
)

# Include routers
app.include_router(transcript_router, tags=["transcript"])

# Mount static files for demo page
from pathlib import Path
demo_path = Path(__file__).parent.parent / "public" / "demo"

# Security: Validate demo directory before mounting
if demo_path.exists():
    # Resolve to absolute path and check it's a real directory (not a symlink)
    resolved_path = demo_path.resolve()

    # Ensure it's within the expected public directory
    expected_base = (Path(__file__).parent.parent / "public").resolve()

    if resolved_path.is_dir() and resolved_path.is_relative_to(expected_base):
        # Additional check: ensure the path itself isn't a symlink
        if not demo_path.is_symlink():
            app.mount("/demo", StaticFiles(directory=str(demo_path), html=True), name="demo")
            logger.info(f"Demo page mounted at /demo -> {resolved_path}")
        else:
            logger.warning("Demo directory is a symlink - not mounting for security")
    else:
        logger.warning(f"Demo path validation failed - not mounting")
else:
    logger.info("Demo directory not found - skipping demo page mount")


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
