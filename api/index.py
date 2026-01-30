import sys
import os

# Add project root to Python path FIRST
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LAZY IMPORT PATTERN: Delay FastAPI app creation until handler is called
# This prevents Vercel's inspection code from walking FastAPI's MRO during import
# Vercel inspects handler.__class__.__mro__ during import, and FastAPI's MRO
# contains non-class items that cause issubclass() to fail

class VercelHandler:
    """
    Wrapper class that Vercel can safely inspect.
    Only creates FastAPI app and Mangum handler when __call__ is invoked.
    This prevents Vercel from walking FastAPI's MRO during import inspection.
    """
    def __init__(self):
        self._mangum_handler = None
    
    def _get_mangum_handler(self):
        """Lazy creation of Mangum handler - only created when handler is called."""
        if self._mangum_handler is None:
            from mangum import Mangum
            from app.main import app
            self._mangum_handler = Mangum(app, lifespan="off")
        return self._mangum_handler
    
    def __call__(self, event, context):
        """Vercel serverless function handler."""
        mangum_handler = self._get_mangum_handler()
        return mangum_handler(event, context)

# Create handler instance - Vercel will inspect this class, not FastAPI's MRO
# The class has a simple MRO: (VercelHandler, object) - safe for issubclass() checks
handler = VercelHandler()

