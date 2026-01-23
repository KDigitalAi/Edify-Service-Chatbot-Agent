"""
Vercel serverless function handler for FastAPI application.
This file is the entry point for Vercel deployments.
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Vercel expects the handler to be the ASGI application
# FastAPI is an ASGI application, so we can export it directly
handler = app

