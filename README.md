# Edify SalesBot - CRM Agentic AI Service

A comprehensive AI-powered CRM chatbot service for the Edify Admin platform that provides intelligent access to CRM data sources through natural language conversations. Built with **LangGraph** for orchestration, **OpenAI GPT-4** for natural language understanding, and **Supabase** for data storage and retrieval.

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Core Functionalities](#core-functionalities)
- [API Endpoints](#api-endpoints)
- [LangGraph Workflow](#langgraph-workflow)
- [Database Schema](#database-schema)
- [Deployment](#deployment)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

SalesBot is a CRM-focused agentic AI that provides comprehensive CRM operations through natural language interactions. The system enables users to:

- **Query CRM Data**: Access leads, campaigns, tasks, trainers, learners, courses, activities, and notes
- **Manage Follow-ups**: Identify leads requiring follow-up based on `next_follow_up` dates
- **Generate Email Drafts**: Create professional email drafts using AI based on lead context
- **Send Emails**: Send emails directly to leads via SMTP
- **View Lead Summaries**: Get comprehensive activity summaries for any lead
- **Perform CRUD Operations**: Create, read, update, and delete CRM records through natural language

The system uses **LangGraph** for stateful workflow orchestration, **OpenAI GPT-4** for intelligent intent detection and response formatting, and **Supabase** for data persistence.

## ✨ Key Features

### 1. **Intelligent Intent Detection**
- **Greeting Detection**: Recognizes greetings and responds appropriately
- **Follow-up Queries**: Identifies requests for leads requiring follow-up
- **Email Draft Requests**: Detects when users want to generate email drafts
- **Email Sending**: Recognizes explicit email sending requests
- **Lead Summary Requests**: Identifies requests for comprehensive lead activity summaries
- **CRM Queries**: Routes all other queries to CRM data access

Priority order: **Greeting → Send Email → Follow-up → Email Draft → Lead Summary → CRM**

### 2. **Follow-up Lead Management**
- Automatically identifies leads requiring follow-up based on `next_follow_up` date
- Filters out closed/lost leads
- Returns formatted list of leads sorted by follow-up date
- Supports queries like:
  - "Which leads need follow up today?"
  - "Show me leads requiring follow-up"
  - "Who needs follow up?"

### 3. **Smart Email Draft Assistant**
- **Context-Aware Drafting**: Analyzes lead's latest interaction (calls, emails, meetings, notes)
- **Template Selection**: Automatically selects appropriate template based on:
  - Latest interaction type
  - Lead status and opportunity stage
  - Time since last interaction
  - Objection handling needs
- **Template Types**:
  - **Follow-up Email**: After calls with no response
  - **Proposal Email**: When opportunity status is "Visiting"
  - **Re-engagement Email**: No interaction for extended period
  - **Meeting Confirmation**: When meeting is scheduled
  - **Objection Handling**: When price/objection keywords detected
- **LLM-Powered**: Uses GPT-4 to generate personalized, professional email content
- **Fallback Templates**: Static templates if LLM generation fails

### 4. **Email Sending (SMTP)**
- **SMTP Integration**: Sends emails via configured SMTP server
- **Template-Based Sending**: Supports introduction, follow-up, and meeting reminder templates
- **Email Validation**: Validates recipient email addresses
- **Error Handling**: Comprehensive error handling for SMTP failures
- **Email Tracking**: Records sent emails in `emails` table
- **Configuration**: SMTP settings via environment variables

### 5. **Lead Activity Summary**
- **Comprehensive View**: Fetches all activities for a lead:
  - Calls (inbound/outbound)
  - Emails (sent/received)
  - Meetings (scheduled/completed)
  - Notes (all notes related to lead)
- **Dynamic Lead Identification**: Works with lead ID or name (case-insensitive)
- **Activity Timeline**: Chronological timeline of recent activities
- **LLM Formatting**: Uses GPT-4 to format summary in natural language
- **Fallback Formatting**: Structured text format if LLM unavailable

### 6. **CRM Data Access (Full CRUD)**
- **Supported Tables**:
  - `campaigns`: Marketing campaigns
  - `leads`: Customer leads and prospects
  - `tasks`: Task management
  - `trainers`: Trainer profiles
  - `learners`: Learner profiles
  - `Course`: Course catalog
  - `activity`: Activity logs
  - `notes`: Notes and comments
  - `batches`: Training batches
  - `emails`: Email records
  - `calls`: Call records
  - `meetings`: Meeting records
  - `messages`: Message records
- **Operations**: Create, Read, Update, Delete for all tables
- **Smart Table Detection**: Automatically detects target table from query keywords
- **Date Filtering**: Supports "today", "yesterday", "this week", "new" queries
- **Text Search**: Multi-field text search across relevant columns
- **Pagination**: Built-in pagination support

### 7. **Conversation Memory**
- Maintains context across conversation turns
- Loads last 5 conversation pairs from database
- Persists all conversations to `chat_history` table
- Tracks source type for each interaction

### 8. **Session Management**
- Anonymous session support
- Authenticated session support (with admin_id)
- Automatic session creation
- Session validation on each request
- Last activity tracking

### 9. **Tool Registry System**
- Comprehensive tool registry for CRUD operations
- Tool validation and error handling
- Destructive action confirmation support
- Automatic tool schema generation for LLM

### 10. **Advanced Features**
- **Date Filtering**: Support for "today", "yesterday", "this week", "new" queries
- **Smart Table Detection**: Automatically detects which table to query based on keywords
- **Response Formatting**: Clean, readable responses with numbered lists and structured data
- **Error Handling**: Graceful error handling with fallback mechanisms
- **Rate Limiting**: Optional rate limiting for API protection
- **Caching**: Optional Redis caching for improved performance
- **Response Compression**: Optional GZip compression for faster responses
- **Audit Logging**: Comprehensive logging of all actions and queries

## 🏗️ Architecture

### System Architecture

```
┌─────────────────┐
│   API Client    │
│  (Frontend/API) │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│   FastAPI       │
│   Application   │
│  (app/main.py)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LangGraph     │
│   Workflow      │
│  (graph.py)     │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  CRM   │ │ Follow-│ │ Email  │ │ Lead   │ │ Memory │
│  Repo  │ │  up    │ │ Draft  │ │Summary │ │  Repo  │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │         │          │          │          │
    └─────────┴──────────┴──────────┴──────────┘
              │
         ┌────▼────┐
         │Supabase│
         │Database│
         └────────┘
```

### LangGraph Workflow

The chatbot uses a state machine workflow with conditional routing:

```
START
  │
  ▼
[validate_session]
  │
  ├─→ Error → [save_memory] → END
  └─→ Success
      │
      ▼
[load_memory]
  │
  ├─→ Greeting → [check_context] → [save_memory] → END
  ├─→ Follow-up → [fetch_followup_leads] → [save_memory] → END
  ├─→ Send Email → [send_email] → [save_memory] → END
  ├─→ Email Draft → [generate_email_draft] → [save_memory] → END
  ├─→ Lead Summary → [fetch_lead_activity_summary] → [save_memory] → END
  └─→ CRM → [fetch_crm] → [check_context] → [call_llm] → [execute_action] → [save_memory] → END
```

### Node Descriptions

1. **validate_session**: Validates session ID, creates new session if needed
2. **load_memory**: Loads last 5 conversation turns from database, detects intent
3. **decide_source**: Uses keyword matching to determine data source (handled in load_memory)
4. **fetch_followup_leads**: Retrieves leads requiring follow-up
5. **fetch_lead_activity_summary**: Fetches comprehensive lead activity summary
6. **generate_email_draft**: Generates AI-powered email drafts
7. **send_email**: Sends emails via SMTP
8. **fetch_crm**: Retrieves CRM data based on query
9. **check_context**: Validates retrieved data, handles empty results
10. **call_llm**: Formats response using OpenAI GPT-4, handles tool calls
11. **execute_action**: Executes CRUD operations via tool registry
12. **save_memory**: Persists conversation to `chat_history` table

## 📁 Project Structure

```
Edify-Service-Chatbot-Agent/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py          # Chat endpoints (/chat/message, /chat/history)
│   │   │   ├── session.py       # Session management (/session/start, /session/end)
│   │   │   └── health.py         # Health check endpoint
│   │   └── dependencies.py      # API dependencies
│   ├── core/
│   │   ├── config.py            # Configuration management (Settings, env vars)
│   │   ├── logging.py            # Logging setup
│   │   ├── security.py           # Security utilities
│   │   └── contants.py           # Constants
│   ├── db/
│   │   ├── supabase.py           # Supabase client initialization (dual instances)
│   │   ├── crm_repo.py           # CRM data repository (CRUD operations)
│   │   ├── memory_repo.py        # Conversation memory repository
│   │   ├── chat_history_repo.py  # Chat history persistence
│   │   ├── retrieved_context_repo.py # Context tracking
│   │   └── audit_repo.py         # Audit logging
│   ├── langgraph/
│   │   ├── state.py              # Agent state definition
│   │   ├── graph.py              # LangGraph workflow definition
│   │   └── nodes/
│   │       ├── validate_session.py    # Session validation node
│   │       ├── load_memory.py         # Memory loading and intent detection
│   │       ├── decide_source.py       # Intent detection logic
│   │       ├── fetch_crm.py           # CRM data fetching
│   │       ├── fetch_followup_leads.py # Follow-up leads fetching
│   │       ├── fetch_lead_activity_summary.py # Lead summary fetching
│   │       ├── generate_email_draft.py # Email draft generation
│   │       ├── send_email_node.py      # Email sending
│   │       ├── check_context.py       # Context validation
│   │       ├── call_llm.py             # LLM response formatting
│   │       ├── execute_action.py       # Tool execution
│   │       └── save_memory.py          # Memory persistence
│   ├── llm/
│   │   ├── openai_client.py     # OpenAI client wrapper
│   │   └── formatter.py          # Response formatting utilities
│   ├── services/
│   │   ├── chat_service.py       # Chat orchestration service
│   │   ├── session_service.py    # Session management service
│   │   ├── followup_service.py   # Follow-up lead service
│   │   ├── lead_summary_service.py # Lead activity summary service
│   │   ├── email_draft_service.py  # Email draft generation service
│   │   ├── email_sender_service.py  # SMTP email sending service
│   │   └── tool_registry.py      # CRUD tool registry
│   ├── utils/
│   │   ├── cache.py              # Caching utilities (Redis)
│   │   └── retry.py              # Retry utilities
│   └── migrations/
│       └── schema.sql            # Database schema
├── scripts/
│   ├── check-runner.sh           # Health check script
│   └── deploy.sh                  # Deployment script
├── nginx/
│   └── edify-chatbot.conf        # Nginx configuration
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker container configuration
├── docker-compose.yml            # Docker Compose configuration
├── docker-compose.prod.yml       # Production Docker Compose
└── README.md                     # This file
```

## 🚀 Installation & Setup

### Prerequisites

- Python 3.11+
- Supabase account (2 instances: Edify and Chatbot)
- OpenAI API key
- (Optional) Redis for caching
- (Optional) Docker for containerized deployment

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd Edify-Service-Chatbot-Agent
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Environment Variables

Create a `.env` file in the project root:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Edify Supabase (READ-ONLY for CRM/LMS/RMS data)
EDIFY_SUPABASE_URL=https://your-edify-project.supabase.co
EDIFY_SUPABASE_SERVICE_ROLE_KEY=your_edify_service_role_key

# Chatbot Supabase (READ/WRITE for sessions/memory/RAG)
CHATBOT_SUPABASE_URL=https://your-chatbot-project.supabase.co
CHATBOT_SUPABASE_SERVICE_ROLE_KEY=your_chatbot_service_role_key

# Environment Configuration
ENV=local
LOG_LEVEL=INFO

# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true
EMAIL_FROM_NAME=Edify Sales Team

# Optional: Rate Limiting
ENABLE_RATE_LIMITING=false
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100

# Optional: Caching (Redis)
ENABLE_CACHING=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Optional: Connection Pooling
ENABLE_CONNECTION_POOLING=false
MAX_CONNECTIONS=100

# Optional: Request Timeout
ENABLE_REQUEST_TIMEOUT=false
REQUEST_TIMEOUT_SECONDS=30

# CORS Configuration
CORS_ALLOW_ORIGINS=*

# Optional: Response Compression
ENABLE_COMPRESSION=false

# Pagination
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=200
```

### Step 5: Database Setup

1. **Chatbot Supabase Database**: Run the migration script in `app/migrations/schema.sql` in your Chatbot Supabase SQL Editor.

2. **Edify Supabase Database**: Ensure you have read-only access to:
   - CRM tables: `campaigns`, `leads`, `tasks`, `trainers`, `learners`, `Course`, `activity`, `notes`
   - Additional tables: `batches`, `emails`, `calls`, `meetings`, `messages`

### Step 6: Run Application

```bash
# Development server (default port 8000)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The application will be available at:
- **API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

## ⚙️ Configuration

### Required Configuration

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 |
| `EDIFY_SUPABASE_URL` | Edify Supabase project URL |
| `EDIFY_SUPABASE_SERVICE_ROLE_KEY` | Edify Supabase service role key (read-only) |
| `CHATBOT_SUPABASE_URL` | Chatbot Supabase project URL |
| `CHATBOT_SUPABASE_SERVICE_ROLE_KEY` | Chatbot Supabase service role key (read/write) |

### SMTP Email Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USERNAME` | SMTP username (sender email) | - |
| `SMTP_PASSWORD` | SMTP password (app password) | - |
| `SMTP_USE_TLS` | Use TLS encryption | `true` |
| `EMAIL_FROM_NAME` | Sender display name | `Edify Sales Team` |

### Optional Optimizations

All optimization features are **disabled by default** and can be enabled via environment variables:

- **Rate Limiting**: Protect API from abuse
- **Caching**: Redis caching for improved performance
- **Connection Pooling**: Optimize database connections
- **Request Timeout**: Prevent long-running requests
- **Response Compression**: GZip compression for responses

## 🔄 Core Functionalities

### 1. Follow-up Lead Management

**Service**: `FollowUpService`

**Functionality**:
- Queries leads where `next_follow_up <= NOW()` and `lead_status NOT IN ('Closed', 'Lost')`
- Returns formatted list sorted by follow-up date (oldest first)

**Example Queries**:
- "Which leads need follow up today?"
- "Show me leads requiring follow-up"
- "Who needs follow up?"

**Node**: `fetch_followup_leads_node`

### 2. Smart Email Draft Generation

**Service**: `EmailDraftService`

**Functionality**:
- Extracts lead identifier (ID or name) from query
- Fetches lead details and latest interaction
- Determines template type based on context:
  - **Follow-up**: Last interaction was call with no response
  - **Proposal**: Opportunity status is "Visiting"
  - **Re-engagement**: No interaction for extended period
  - **Meeting Confirmation**: Meeting scheduled
  - **Objection Handling**: Price/objection keywords detected
- Generates email draft using GPT-4 with lead context
- Falls back to static templates if LLM fails

**Example Queries**:
- "Draft follow-up email for lead Guna"
- "Write email for lead 132"
- "Compose proposal email for lead John"

**Node**: `generate_email_draft_node`

### 3. Email Sending

**Service**: `EmailSenderService`, `EmailDraftService`

**Functionality**:
- Extracts lead identifier from query
- Validates lead email address
- Sends email via SMTP using configured credentials
- Records email in `emails` table
- Supports template-based sending (introduction, follow-up, meeting reminder)

**Example Queries**:
- "Send follow-up email to lead Guna"
- "Send email to lead 132"
- "Send introduction email to lead John"

**Node**: `send_email_node`

### 4. Lead Activity Summary

**Service**: `LeadSummaryService`

**Functionality**:
- Extracts lead identifier (ID or name, case-insensitive)
- Fetches lead details
- Retrieves all activities:
  - Calls (inbound/outbound)
  - Emails (sent/received)
  - Meetings (scheduled/completed)
  - Notes (all notes)
- Builds chronological timeline
- Formats summary using GPT-4
- Falls back to structured text if LLM unavailable

**Example Queries**:
- "Give me full summary of lead Guna"
- "Show activity summary for lead 132"
- "What's the history of lead John?"

**Node**: `fetch_lead_activity_summary_node`

### 5. CRM Data Access

**Service**: `CRMRepo`

**Functionality**:
- Full CRUD operations on all CRM tables
- Smart table detection from query keywords
- Date filtering ("today", "yesterday", "this week", "new")
- Multi-field text search
- Pagination support

**Supported Tables**:
- `campaigns`, `leads`, `tasks`, `trainers`, `learners`, `Course`, `activity`, `notes`
- `batches`, `emails`, `calls`, `meetings`, `messages`

**Example Queries**:
- "Show me all leads"
- "List trainers in New York"
- "What campaigns are active?"
- "Show me tasks due today"
- "Create a new lead named John Doe"

**Node**: `fetch_crm_node` → `call_llm_node` → `execute_action_node`

## 🔌 API Endpoints

### Session Management

#### `POST /session/start-anonymous`
Start an anonymous session.

**Response:**
```json
{
  "session_id": "uuid",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### `POST /session/start`
Start a session with admin ID.

**Request:**
```json
{
  "admin_id": "optional-admin-id"
}
```

#### `POST /session/end`
End a session.

**Request:**
```json
{
  "session_id": "uuid"
}
```

### Chat

#### `POST /chat/message`
Send a chat message and get AI response.

**Request:**
```json
{
  "message": "Show me all leads",
  "session_id": "uuid"
}
```

**Response:**
```json
{
  "response": "Here are all the leads...",
  "session_id": "uuid"
}
```

#### `GET /chat/history/{session_id}`
Retrieve chat history for a session.

**Query Parameters:**
- `limit` (optional): Number of records (1-200, default: 50)

**Response:**
```json
{
  "session_id": "uuid",
  "count": 10,
  "history": [
    {
      "id": 1,
      "session_id": "uuid",
      "admin_id": "anonymous",
      "user_message": "Show me all leads",
      "assistant_response": "Here are all the leads...",
      "source_type": "crm",
      "response_time_ms": 1234,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Health Check

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "Edify Admin AI Agent"
}
```

## 🗄️ Database Schema

### Chatbot Supabase Tables

#### `admin_sessions`
Stores user sessions.

| Column | Type | Description |
|--------|------|-------------|
| session_id | UUID | Primary key |
| admin_id | UUID | User identifier |
| status | TEXT | active/ended/expired |
| created_at | TIMESTAMP | Session creation time |
| last_activity | TIMESTAMP | Last activity time |
| ended_at | TIMESTAMP | Session end time |

#### `chat_history`
Stores complete conversation pairs.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| session_id | UUID | Foreign key to admin_sessions |
| admin_id | UUID | User identifier |
| user_message | TEXT | User's message |
| assistant_response | TEXT | Bot's response |
| source_type | TEXT | crm/followup/email_draft/send_email/lead_summary/none |
| response_time_ms | INTEGER | Response time |
| tokens_used | INTEGER | Token count (optional) |
| created_at | TIMESTAMP | Creation time |

#### `retrieved_context`
Tracks all data retrieval operations.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| session_id | UUID | Foreign key |
| admin_id | UUID | User identifier |
| source_type | TEXT | crm/followup/email_draft/send_email/lead_summary |
| query_text | TEXT | Original query |
| record_count | INTEGER | Number of records retrieved |
| payload | JSONB | Retrieved data |
| error_message | TEXT | Error if any |
| retrieval_time_ms | INTEGER | Retrieval time |
| created_at | TIMESTAMP | Creation time |

#### `audit_logs`
Comprehensive audit trail.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| admin_id | UUID | User identifier |
| session_id | UUID | Session identifier |
| action | TEXT | Action name |
| metadata | JSONB | Action details |
| created_at | TIMESTAMP | Creation time |

### Edify Supabase Tables (Read-Only)

#### CRM Tables
- `campaigns`: Marketing campaigns
- `leads`: Customer leads (includes `next_follow_up`, `lead_status`, `lead_owner`)
- `tasks`: Task management
- `trainers`: Trainer information
- `learners`: Learner information
- `Course`: Course catalog
- `activity`: Activity logs
- `notes`: Notes and comments
- `batches`: Training batches
- `emails`: Email records
- `calls`: Call records
- `meetings`: Meeting records
- `messages`: Message records

## 🚢 Deployment

### Quick Start - Docker Deployment

#### Build the Docker Image

```bash
docker build -t edify-chatbot .
```

#### Run the Container

**Using environment file (default port 8080):**
```bash
docker run -d \
  --name edify-chatbot \
  -p 8080:8080 \
  --env-file .env \
  edify-chatbot
```

#### Docker Compose (Recommended)

```bash
# Use default port 8080
docker-compose up -d

# Or use a custom port
PORT=8081 docker-compose up -d
```

### Production Deployment

For production, consider:

1. **Use a reverse proxy** (nginx, Traefik) in front of the container
2. **Set up proper logging** with volume mounts
3. **Use Docker secrets** or a secrets management service
4. **Configure resource limits** in docker-compose or Kubernetes
5. **Set up health checks** and monitoring

### Environment-Specific Configuration

- **Development**: `ENV=local`
- **Staging**: `ENV=staging`
- **Production**: `ENV=production`

## 💻 Development

### Code Structure

- **Repositories** (`app/db/*_repo.py`): Data access layer, no business logic
- **Services** (`app/services/`): Business logic and orchestration
- **Nodes** (`app/langgraph/nodes/`): Workflow nodes, single responsibility
- **Routes** (`app/api/routes/`): API endpoints, request/response handling

### Adding a New Feature

1. Create service in `app/services/` (if needed)
2. Create node in `app/langgraph/nodes/` (if needed)
3. Add intent detection in `decide_source.py`
4. Add node to `graph.py` workflow
5. Update routing logic

### Code Style

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Log important operations

## 🧪 Testing

### Manual Testing

1. **Start the server:**
```bash
uvicorn app.main:app --reload
```

2. **Test via Interactive UI:**
Navigate to `http://localhost:8000/docs`

3. **Test via API:**
```bash
# Start session
curl -X POST http://localhost:8000/session/start-anonymous

# Send message
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me all leads", "session_id": "your-session-id"}'
```

### Unit Testing

```bash
pytest
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Supabase Connection Errors
- **Issue**: Cannot connect to Supabase
- **Solution**: Verify environment variables and network connectivity

#### 2. OpenAI API Errors
- **Issue**: OpenAI API key invalid or rate limited
- **Solution**: Check API key and usage limits

#### 3. Email Sending Fails
- **Issue**: SMTP authentication fails
- **Solution**: Verify SMTP credentials, check app password for Gmail

#### 4. Lead Not Found
- **Issue**: Lead identifier not recognized
- **Solution**: Ensure lead ID is numeric or name matches exactly (case-insensitive)

#### 5. Session Not Found
- **Issue**: Session ID not recognized
- **Solution**: Sessions are created automatically, ensure session_id is valid UUID

### Debugging

Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

Check logs for:
- Database queries
- API calls
- Error messages
- Performance metrics

### Performance Optimization

1. **Enable Caching:**
```env
ENABLE_CACHING=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

2. **Enable Connection Pooling:**
```env
ENABLE_CONNECTION_POOLING=true
MAX_CONNECTIONS=100
```

3. **Enable Response Compression:**
```env
ENABLE_COMPRESSION=true
```

4. **Set Request Timeout:**
```env
ENABLE_REQUEST_TIMEOUT=true
REQUEST_TIMEOUT_SECONDS=30
```

## 📝 License

[Your License Here]

## 👥 Contributors

[Your Contributors Here]

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Contact the development team

---

**Built with ❤️ for Edify Admin Platform**
