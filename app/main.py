from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import session, chat, health
import os
import logging

logger = logging.getLogger(__name__)
setup_logging()

app = FastAPI(
    title="Edify Admin AI Service Agent",
    version="1.0.0",
)

# Configure CORS (optional: configurable origins)
cors_origins = ["*"]
if settings.CORS_ALLOW_ORIGINS != "*":
    cors_origins = [origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",")]
    logger.info(f"CORS configured for origins: {cors_origins}")
else:
    logger.warning("CORS allows all origins - consider restricting in production")

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
# Only /chat endpoints are rate limited - health and static routes are excluded
if settings.ENABLE_RATE_LIMITING:
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded
        
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_PER_MINUTE}/min, {settings.RATE_LIMIT_PER_HOUR}/hour")
        logger.info("Rate limiting will be applied to /chat endpoints only (health and static routes excluded)")
    except ImportError:
        logger.warning("slowapi not installed - rate limiting disabled. Install with: pip install slowapi")
        settings.ENABLE_RATE_LIMITING = False

# Serve static files (frontend)
# Get the project root directory (one level up from app/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(project_root, "static")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Serve index.html at root
    @app.get("/")
    async def read_root():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend not found. Please ensure static/index.html exists."}
else:
    @app.get("/")
    async def read_root():
        return {"message": "Frontend directory not found. Please ensure static/ directory exists."}

app.include_router(session.router, prefix="/session", tags=["Session"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(health.router, tags=["Health"])

# Interactive chat interface for testing at /docs
@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def interactive_chat():
    """Interactive chat interface for testing the chatbot."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chatbot Test Interface - Edify Admin AI</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .chat-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 800px;
            height: 90vh;
            max-height: 700px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .chat-header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        .chat-header .session-info {
            font-size: 12px;
            opacity: 0.9;
            margin-top: 5px;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .message {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.user {
            flex-direction: row-reverse;
        }
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
            flex-shrink: 0;
        }
        .message.user .message-avatar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .message.assistant .message-avatar {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            line-height: 1.5;
        }
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.assistant .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        .message-content p {
            margin: 5px 0;
        }
        .message-content strong {
            font-weight: 600;
        }
        .message-content ul, .message-content ol {
            margin: 10px 0;
            padding-left: 20px;
        }
        .message-content li {
            margin: 5px 0;
        }
        .loading {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .chat-input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        .chat-form {
            display: flex;
            gap: 10px;
        }
        .chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        .chat-input:focus {
            border-color: #667eea;
        }
        .send-button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .send-button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .send-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .error-message {
            background: #fee;
            color: #c33;
            padding: 12px 16px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid #c33;
        }
        .welcome-message {
            text-align: center;
            color: #666;
            padding: 20px;
            background: white;
            border-radius: 12px;
            margin: 20px;
        }
        .welcome-message h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>🤖 Edify Admin AI Chatbot</h1>
            <div class="session-info">Session: <span id="sessionId">Initializing...</span></div>
        </div>
        <div class="chat-messages" id="chatMessages">
            <div class="welcome-message">
                <h3>Welcome to Chatbot Test Interface</h3>
                <p>This interface allows you to test the chatbot directly.</p>
                <p>Session is being initialized...</p>
            </div>
        </div>
        <div class="chat-input-container">
            <form class="chat-form" id="chatForm">
                <input 
                    type="text" 
                    class="chat-input" 
                    id="messageInput" 
                    placeholder="Type your message here..." 
                    autocomplete="off"
                    required
                    disabled
                >
                <button type="submit" class="send-button" id="sendButton" disabled>
                    Send
                </button>
            </form>
        </div>
    </div>

    <script>
        let currentSessionId = null;
        const API_BASE = window.location.origin;
        
        const chatMessages = document.getElementById('chatMessages');
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const sessionIdDisplay = document.getElementById('sessionId');
        
        // Initialize session on page load
        async function initializeSession() {
            try {
                const response = await fetch(`${API_BASE}/session/start-anonymous`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to start session');
                }
                
                const data = await response.json();
                currentSessionId = data.session_id;
                sessionIdDisplay.textContent = currentSessionId.substring(0, 8) + '...';
                
                // Clear welcome message and enable input
                chatMessages.innerHTML = '';
                messageInput.disabled = false;
                sendButton.disabled = false;
                messageInput.focus();
                
                addMessage('assistant', 'Hello! I\'m the Edify Admin AI Assistant. How can I help you today?');
            } catch (error) {
                console.error('Session initialization error:', error);
                chatMessages.innerHTML = `
                    <div class="error-message">
                        <strong>Error:</strong> Failed to initialize session. ${error.message}
                        <br><br>
                        <button onclick="location.reload()" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer;">
                            Retry
                        </button>
                    </div>
                `;
            }
        }
        
        // Add message to chat
        function addMessage(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = role === 'user' ? 'U' : 'AI';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.innerHTML = formatMessage(content);
            
            messageDiv.appendChild(avatar);
            messageDiv.appendChild(contentDiv);
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Format message content (basic markdown support)
        function formatMessage(text) {
            if (!text) return '';
            
            // Escape HTML first
            let html = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            
            // Convert markdown-style formatting
            html = html.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
            html = html.replace(/\\n/g, '<br>');
            
            // Convert numbered lists (split by lines first)
            const lines = html.split('<br>');
            const formattedLines = lines.map(line => {
                const listMatch = line.match(/^(\\d+)\\.\\s+(.+)$/);
                if (listMatch) {
                    return '<p><strong>' + listMatch[1] + '.</strong> ' + listMatch[2] + '</p>';
                }
                return line ? '<p>' + line + '</p>' : '';
            });
            html = formattedLines.join('');
            
            return html;
        }
        
        // Handle form submission
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const message = messageInput.value.trim();
            if (!message || !currentSessionId) return;
            
            // Add user message
            addMessage('user', message);
            messageInput.value = '';
            
            // Disable input
            messageInput.disabled = true;
            sendButton.disabled = true;
            sendButton.innerHTML = '<span class="loading"></span>';
            
            try {
                const response = await fetch(`${API_BASE}/chat/message`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: currentSessionId
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                    throw new Error(errorData.detail || `HTTP ${response.status}: Failed to get response`);
                }
                
                const data = await response.json();
                
                // Update session ID if changed
                if (data.session_id && data.session_id !== currentSessionId) {
                    currentSessionId = data.session_id;
                    sessionIdDisplay.textContent = currentSessionId.substring(0, 8) + '...';
                }
                
                // Add assistant response
                addMessage('assistant', data.response);
                
            } catch (error) {
                console.error('Chat error:', error);
                addMessage('assistant', `Error: ${error.message || 'Failed to send message. Please try again.'}`);
            } finally {
                // Re-enable input
                messageInput.disabled = false;
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
                messageInput.focus();
            }
        });
        
        // Initialize on page load
        initializeSession();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
