from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import session, chat, health
import logging
import os

logger = logging.getLogger(__name__)
setup_logging()

app = FastAPI(
    title="Edify Admin AI Service Agent",
    version="1.0.0",
)

# Configure CORS (environment-aware: restrictive in production, permissive in development)
# Edify Web App URL - Always allowed for integration
EDIFY_WEB_APP_URL = "https://edify-enterprise-web-app-git-dev-tech-kdigitalais-projects.vercel.app"

if settings.CORS_ALLOW_ORIGINS != "*":
    # Explicit origins configured - add Edify web app URL
    cors_origins = [origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
    # Ensure Edify web app URL is included
    if EDIFY_WEB_APP_URL not in cors_origins:
        cors_origins.append(EDIFY_WEB_APP_URL)
    logger.info(f"CORS configured for origins: {cors_origins}")
    logger.info(f"Edify web app URL included: {EDIFY_WEB_APP_URL}")
elif settings.ENV in ("local", "development", "dev"):
    # Development: allow all origins (convenient for local testing)
    # "*" already allows all origins including Edify web app
    cors_origins = ["*"]
    logger.info("CORS allows all origins (development mode)")
    logger.info(f"Edify web app URL will be allowed: {EDIFY_WEB_APP_URL}")
else:
    # Production/staging: allow all origins (includes Edify web app)
    cors_origins = ["*"]
    logger.warning(
        f"CORS allows all origins in {settings.ENV} environment - "
        "consider restricting by setting CORS_ALLOW_ORIGINS environment variable"
    )
    logger.info(f"Edify web app URL will be allowed: {EDIFY_WEB_APP_URL}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: Add response compression
if settings.ENABLE_COMPRESSION:
    from fastapi.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    logger.info("Response compression enabled")

# Optional: Add rate limiting (if enabled)
# Note: Rate limiting is applied via decorators on individual routes
# Routes will work without rate limiting if slowapi is not installed
# Only /chat endpoints are rate limited - health routes are excluded
if settings.ENABLE_RATE_LIMITING:
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded
        
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_PER_MINUTE}/min, {settings.RATE_LIMIT_PER_HOUR}/hour")
        logger.info("Rate limiting will be applied to /chat endpoints only (health routes excluded)")
    except ImportError:
        logger.warning("slowapi not installed - rate limiting disabled. Install with: pip install slowapi")
        settings.ENABLE_RATE_LIMITING = False

# Serve static files (frontend)
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Serving static files from: {static_dir}")

# Root endpoint - Serve frontend or API info
@app.get("/")
async def read_root():
    """
    Root endpoint - serves frontend if available, otherwise returns API info.
    """
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "service": "SalesBot - CRM Agentic AI",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "frontend": "/static/index.html"
    }

# Include API routers
app.include_router(session.router, prefix="/session", tags=["Session"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(health.router, tags=["Health"])
