# API Endpoints Analysis & Frontend Integration Guide

## API Endpoints Overview

### 1. Session Management

#### POST `/session/start-anonymous`
- **Purpose**: Start a new anonymous session
- **Authentication**: None required
- **Request Body**: None (optional `StartSessionRequest` with `admin_id`)
- **Response**: 
  ```json
  {
    "session_id": "uuid-string",
    "status": "active",
    "created_at": "2026-02-13T10:00:00Z"
  }
  ```
- **Usage**: Called automatically on page load to initialize chat session

#### POST `/session/start`
- **Purpose**: Start a session with optional admin_id
- **Request Body**: 
  ```json
  {
    "admin_id": "optional-admin-id"  // defaults to "anonymous"
  }
  ```
- **Response**: Same as `/session/start-anonymous`

#### POST `/session/end`
- **Purpose**: End an active session
- **Request Body**:
  ```json
  {
    "session_id": "uuid-string"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid-string",
    "status": "ended",
    "ended_at": "2026-02-13T10:00:00Z"
  }
  ```

---

### 2. Chat Endpoints

#### POST `/chat/message`
- **Purpose**: Send a chat message and get AI response
- **Rate Limiting**: Optional (if `ENABLE_RATE_LIMITING=true`)
- **Request Body**:
  ```json
  {
    "message": "User's message text",
    "session_id": "uuid-string"
  }
  ```
- **Response**:
  ```json
  {
    "response": "AI assistant response text",
    "session_id": "uuid-string"
  }
  ```
- **Error Handling**: Returns 500 with error detail if processing fails
- **Processing Flow**:
  1. Validates/creates session
  2. Updates session last_activity
  3. Saves user message to chat_history
  4. Invokes LangGraph workflow:
     - Loads conversation memory
     - Detects intent (greeting, follow-up, CRM query, etc.)
     - Routes to appropriate data source
     - Fetches CRM data or follow-up leads
     - Formats response using LLM
  5. Saves assistant response to chat_history
  6. Returns formatted response

#### GET `/chat/history/{session_id}`
- **Purpose**: Retrieve chat history for a session
- **Query Parameters**:
  - `limit` (optional): Number of records to return (1-200, default: 50)
- **Response**:
  ```json
  {
    "session_id": "uuid-string",
    "count": 10,
    "history": [
      {
        "id": 1,
        "session_id": "uuid-string",
        "admin_id": "anonymous",
        "user_message": "User's message",
        "assistant_response": "AI response",
        "source_type": "crm" | "followup" | "general",
        "response_time_ms": 1234,
        "tokens_used": null,
        "created_at": "2026-02-13T10:00:00Z"
      }
    ]
  }
  ```
- **Usage**: Display conversation history in modal

---

### 3. Health Check

#### GET `/health`
- **Purpose**: Check API health status
- **Response**:
  ```json
  {
    "status": "ok",
    "service": "Edify Admin AI Agent"
  }
  ```
- **Usage**: Verify API connectivity on page load

---

## API Request/Response Flow

### Chat Message Flow:
```
Frontend → POST /chat/message
  ↓
Backend validates session (creates if needed)
  ↓
ChatService.process_user_message()
  ↓
LangGraph Workflow:
  ├─ validate_session_node
  ├─ load_memory_node
  ├─ decide_source_node (detects intent)
  ├─ fetch_crm_node OR fetch_followup_leads_node
  ├─ check_context_node
  ├─ call_llm_node (formats response)
  ├─ execute_action_node (if tool calls needed)
  └─ save_memory_node
  ↓
Response saved to chat_history
  ↓
Frontend receives response
```

### Intent Detection:
- **Greetings**: "hello", "hi", "hey" → `source_type: "none"`
- **Follow-up Queries**: "follow up", "leads to call", "pending leads" → `source_type: "followup"`
- **CRM Queries**: Everything else → `source_type: "crm"`

---

## Frontend Integration

### File Structure:
```
static/
├── index.html      # Main HTML structure
├── styles.css      # Styling and responsive design
└── app.js          # JavaScript API integration
```

### Key Features:
1. **Auto Session Management**: Automatically creates session on page load
2. **Real-time Chat**: Send messages and receive responses
3. **Message History**: View past conversations
4. **Status Indicator**: Shows connection status
5. **Responsive Design**: Works on desktop and mobile
6. **Error Handling**: Graceful error messages
7. **Loading States**: Visual feedback during API calls

### API Integration Points:

#### 1. Session Initialization (`app.js:initializeSession`)
```javascript
const response = await fetch(`${API_BASE_URL}/session/start-anonymous`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
});
const data = await response.json();
sessionId = data.session_id;
```

#### 2. Send Message (`app.js:handleSendMessage`)
```javascript
const response = await fetch(`${API_BASE_URL}/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: userMessage,
        session_id: sessionId
    })
});
const data = await response.json();
// Display data.response
```

#### 3. Load History (`app.js:showHistory`)
```javascript
const response = await fetch(`${API_BASE_URL}/chat/history/${sessionId}?limit=50`);
const data = await response.json();
// Display data.history
```

---

## Error Handling

### Common Errors:
1. **Session Creation Failed**: Frontend shows error, user can refresh
2. **Message Send Failed**: Error message displayed in chat
3. **History Load Failed**: Error shown in modal
4. **Network Errors**: Status indicator shows "Offline"

### Error Response Format:
```json
{
    "detail": "Error message description"
}
```

---

## CORS Configuration

The backend is configured to allow:
- All origins in development (`CORS_ALLOW_ORIGINS=*`)
- Specific origins in production (configurable)
- Edify web app URLs are always allowed

---

## Rate Limiting

- **Status**: Optional (enabled if `ENABLE_RATE_LIMITING=true`)
- **Limits**: Configurable per minute/hour
- **Scope**: Only applies to `/chat` endpoints
- **Health endpoints**: Not rate limited

---

## Security Considerations

1. **No Authentication Required**: Sessions are anonymous by default
2. **Session Validation**: Backend validates session_id on each request
3. **Input Sanitization**: Frontend escapes HTML to prevent XSS
4. **CORS**: Configured for specific origins in production

---

## Testing the Frontend

1. **Start Backend**: `uvicorn app.main:app --reload`
2. **Open Browser**: Navigate to `http://localhost:8000/`
3. **Test Features**:
   - Send a message: "Which leads need follow up today?"
   - View history: Click "History" button
   - Clear chat: Click "Clear" button
   - Check status: Status indicator in header

---

## Example Queries

### Follow-up Queries:
- "Which leads need follow up today?"
- "Show leads requiring follow up"
- "Leads pending follow up"
- "Followup today"

### CRM Queries:
- "Show me all leads"
- "What campaigns are active?"
- "List all tasks"
- "Find leads by status"

### General Queries:
- "Hello"
- "What can you do?"
- "Help"

---

## Frontend Features

### UI Components:
1. **Header**: Title, action buttons, status indicator
2. **Chat Container**: Message display area with scroll
3. **Input Area**: Text input with send button
4. **History Modal**: Popup showing conversation history
5. **Welcome Message**: Initial greeting with feature list

### Styling:
- Modern gradient design
- Responsive layout (mobile-friendly)
- Smooth animations
- Dark/light theme support
- Accessible color contrast

### JavaScript Features:
- Auto-resize textarea
- Enter to send (Shift+Enter for new line)
- Auto-scroll to latest message
- Loading indicators
- Error handling
- Session persistence

---

## Deployment Notes

1. **Static Files**: Served from `/static` directory
2. **Root Route**: Serves `index.html` if available
3. **API Routes**: Prefixed with `/session`, `/chat`, `/health`
4. **CORS**: Must be configured for production domains

---

## Future Enhancements

1. **WebSocket Support**: Real-time bidirectional communication
2. **File Uploads**: Support for document attachments
3. **Voice Input**: Speech-to-text integration
4. **Export History**: Download chat history as PDF/CSV
5. **Multi-language**: Internationalization support
6. **Dark Mode**: Theme toggle
7. **Notifications**: Browser notifications for responses

