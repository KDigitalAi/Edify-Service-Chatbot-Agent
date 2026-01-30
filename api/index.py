import sys
import os

# Add project root to Python path FIRST
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MINIMAL FUNCTION HANDLER: Simple function with lazy imports
# This prevents Vercel's inspection code from walking FastAPI's MRO during import
# Vercel inspects module namespace at import time - keeping it minimal avoids MRO issues
# All complex imports (FastAPI, Mangum) happen INSIDE the function at runtime

# Global cache for Mangum handler (created on first call)
_mangum_handler = None

def handler(event, context):
    """
    Vercel serverless function handler.
    Creates FastAPI app and Mangum wrapper on-demand to avoid MRO inspection issues.
    All complex imports happen here, not at module level.
    """
    global _mangum_handler
    
    # Lazy initialization - only create handler on first call
    if _mangum_handler is None:
        from mangum import Mangum
        from app.main import app
        _mangum_handler = Mangum(app, lifespan="off")
    
    # Call the Mangum handler
    return _mangum_handler(event, context)

