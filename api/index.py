# ABSOLUTE MINIMAL HANDLER: Only function definition
# Vercel's inspection happens at import - this file has minimal surface area

def handler(event, context):
    """
    Vercel serverless function handler.
    All imports happen inside function to avoid Vercel's MRO inspection.
    """
    # Cache handler on function object (no module-level state)
    if not hasattr(handler, '_cached'):
        import sys
        import os
        
        # Setup Python path
        _current_file = os.path.abspath(__file__)
        _root = os.path.dirname(os.path.dirname(_current_file))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        
        # Lazy import with error handling
        try:
            from mangum import Mangum
            from app.main import app
            handler._cached = Mangum(app, lifespan="off")
        except Exception as e:
            # Return error response if initialization fails
            return {
                'statusCode': 500,
                'body': f'Handler initialization failed: {str(e)}'
            }
    
    # Execute handler
    try:
        return handler._cached(event, context)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Handler execution failed: {str(e)}'
        }

