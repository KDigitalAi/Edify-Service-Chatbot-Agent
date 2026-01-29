"""
Deployment verification script.
Confirms Mangum handler is properly exported at build time.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.index import handler
print("FINAL HANDLER CLASS:", handler.__class__)

