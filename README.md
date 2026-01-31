# Edify Admin AI Service Agent

A comprehensive AI-powered chatbot service for Edify Admin platform that provides intelligent access to CRM, LMS, RMS, and RAG (Retrieval-Augmented Generation) data sources through natural language conversations.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Workflows](#workflows)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Data Sources](#data-sources)
- [Deployment](#deployment)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Edify Admin AI Service Agent is an intelligent chatbot that enables users to query and retrieve information from multiple data sources:

- **CRM (Customer Relationship Management)**: Leads, campaigns, trainers, learners, tasks, activities, notes, courses
- **LMS (Learning Management System)**: Training batches and schedules
- **RMS (Recruitment Management System)**: Job openings, candidates, companies, interviews, tasks
- **RAG (Retrieval-Augmented Generation)**: Knowledge base documents, policies, manuals

The system uses **LangGraph** for orchestration, **OpenAI GPT-4** for natural language understanding, and **Supabase** for data storage and retrieval.

## ✨ Features

### Core Capabilities
- **Multi-Source Data Access**: Seamlessly query CRM, LMS, RMS, and RAG data
- **Intelligent Intent Detection**: Automatically routes queries to the correct data source
- **Conversation Memory**: Maintains context across conversation turns
- **Session Management**: Anonymous and authenticated session support
- **Vector Search**: Semantic search for knowledge base documents
- **Audit Logging**: Comprehensive logging of all actions and queries

### Advanced Features
- **Date Filtering**: Support for "today", "yesterday", "this week", "new" queries
- **Smart Table Detection**: Automatically detects which table to query based on keywords
- **Response Formatting**: Clean, readable responses with numbered lists and structured data
- **Error Handling**: Graceful error handling with fallback mechanisms
- **Rate Limiting**: Optional rate limiting for API protection
- **Caching**: Optional Redis caching for improved performance
- **Response Compression**: Optional GZip compression for faster responses

## 🏗️ Architecture

### System Architecture

```
┌─────────────────┐
│   Frontend      │
│  (HTML/JS)      │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│   FastAPI       │
│   Application   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LangGraph     │
│   Workflow      │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  CRM   │ │  LMS   │ │  RMS   │ │  RAG   │
│  Repo  │ │  Repo  │ │  Repo  │ │ Vector │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │         │          │          │
    └─────────┴──────────┴──────────┘
              │
         ┌────▼────┐
         │Supabase│
         │Database│
         └────────┘
```

### LangGraph Workflow

The chatbot uses a state machine workflow with the following nodes:

1. **validate_session**: Validates and initializes session
2. **load_memory**: Loads conversation history
3. **decide_source**: Determines data source (CRM/LMS/RMS/RAG/general)
4. **fetch_crm/fetch_lms/fetch_rms/fetch_rag**: Retrieves data from respective sources
5. **check_context**: Validates retrieved data
6. **call_llm**: Formats response using OpenAI
7. **save_memory**: Persists conversation to database

### Data Flow

```
User Message
    │
    ▼
Session Validation
    │
    ▼
Load Conversation History
    │
    ▼
Intent Detection (Keyword/LLM)
    │
    ├─→ CRM ──→ Fetch CRM Data
    ├─→ LMS ──→ Fetch LMS Data
    ├─→ RMS ──→ Fetch RMS Data
    └─→ RAG ──→ Vector Search
    │
    ▼
Validate Retrieved Context
    │
    ▼
Format Response (LLM)
    │
    ▼
Save to Database
    │
    ▼
Return Response to User
```

## 📁 Project Structure

```
service_chatbot/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py         # Chat endpoints
│   │   │   ├── session.py      # Session management
│   │   │   └── health.py       # Health check
│   │   └── dependencies.py     # API dependencies
│   ├── core/
│   │   ├── config.py           # Configuration management
│   │   ├── logging.py          # Logging setup
│   │   ├── security.py         # Security utilities
│   │   └── contants.py         # Constants
│   ├── db/
│   │   ├── supabase.py         # Supabase client initialization
│   │   ├── crm_repo.py         # CRM data repository
│   │   ├── lms_repo.py         # LMS data repository
│   │   ├── rms_repo.py         # RMS data repository
│   │   ├── rag_repo.py         # RAG data repository
│   │   ├── memory_repo.py      # Conversation memory
│   │   ├── chat_history_repo.py # Chat history persistence
│   │   ├── retrieved_context_repo.py # Context tracking
│   │   └── audit_repo.py       # Audit logging
│   ├── langgraph/
│   │   ├── state.py            # Agent state definition
│   │   ├── graph.py            # LangGraph workflow definition
│   │   └── nodes/
│   │       ├── validate_session.py
│   │       ├── load_memory.py
│   │       ├── decide_source.py
│   │       ├── fetch_crm.py
│   │       ├── fetch_lms.py
│   │       ├── fetch_rms.py
│   │       ├── fetch_rag.py
│   │       ├── check_context.py
│   │       ├── call_llm.py
│   │       ├── save_memory.py
│   │       └── fallback.py
│   ├── llm/
│   │   ├── openai_client.py    # OpenAI client wrapper
│   │   └── formatter.py        # Response formatting
│   ├── rag/
│   │   ├── embedder.py         # Text embedding
│   │   ├── ingestion.py        # Document ingestion
│   │   └── vector_search.py    # Vector similarity search
│   ├── services/
│   │   ├── chat_service.py     # Chat orchestration service
│   │   └── session_service.py # Session management service
│   ├── utils/
│   │   └── cache.py            # Caching utilities
│   └── migrations/
│       └── schema.sql           # Database schema
├── static/
│   ├── index.html              # Frontend HTML
│   ├── app.js                  # Frontend JavaScript
│   └── styles.css             # Frontend styles
├── scripts/
│   └── pdf_to_embedding.py    # PDF ingestion script
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container configuration
├── .dockerignore              # Docker ignore patterns
└── README.md                   # This file
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
cd service_chatbot
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
   - LMS tables: `batches`
   - RMS tables: `job_openings`, `candidates`, `companies`, `interviews`, `tasks`

### Step 6: Run Application

```bash
# Development server (default port 8000)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server (default port 8000)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or use a different port (e.g., 8080)
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The application will be available at:
- API: `http://localhost:8000` (or your chosen port)
- Interactive Chat: `http://localhost:8000/docs` (or your chosen port)
- Frontend: `http://localhost:8000/` (or your chosen port)
- API Docs: `http://localhost:8000/docs` (Swagger UI)
- OpenAPI Schema: `http://localhost:8000/openapi.json`

> **Note:** If ports 3000 or 8000 are already in use, use port 8080 or any other available port.

## ⚙️ Configuration

### Required Configuration

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 |
| `EDIFY_SUPABASE_URL` | Edify Supabase project URL |
| `EDIFY_SUPABASE_SERVICE_ROLE_KEY` | Edify Supabase service role key (read-only) |
| `CHATBOT_SUPABASE_URL` | Chatbot Supabase project URL |
| `CHATBOT_SUPABASE_SERVICE_ROLE_KEY` | Chatbot Supabase service role key (read/write) |

### Optional Optimizations

All optimization features are **disabled by default** and can be enabled via environment variables:

- **Rate Limiting**: Protect API from abuse
- **Caching**: Redis caching for improved performance
- **Connection Pooling**: Optimize database connections
- **Request Timeout**: Prevent long-running requests
- **Response Compression**: GZip compression for responses

## 🔄 Workflows

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
  ▼
[decide_source]
  │
  ├─→ CRM → [fetch_crm]
  ├─→ LMS → [fetch_lms]
  ├─→ RMS → [fetch_rms]
  ├─→ RAG → [fetch_rag]
  └─→ General → [check_context]
      │
      ▼
[check_context]
  │
  ├─→ No Data → [save_memory] → END
  └─→ Has Data
      │
      ▼
[call_llm]
  │
  ▼
[save_memory]
  │
  ▼
END
```

### Node Descriptions

1. **validate_session**: Validates session ID, creates new session if needed
2. **load_memory**: Loads last 5 conversation turns from database
3. **decide_source**: Uses keyword matching + LLM to determine data source
4. **fetch_***: Retrieves data from respective repositories
5. **check_context**: Validates retrieved data, handles empty results
6. **call_llm**: Formats response using OpenAI GPT-4
7. **save_memory**: Persists conversation to `chat_history` table

### Intent Detection

The system uses a two-stage intent detection:

1. **Keyword Matching** (Fast, LENIENT):
   - CRM: leads, trainers, learners, campaigns, tasks, courses
   - LMS: batches, training schedules
   - RMS: candidates, job openings, interviews, companies
   - RAG: policies, documents, knowledge base

2. **LLM Classification** (Fallback):
   - Used when keywords are ambiguous
   - GPT-4 classifies query into source type

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
| source_type | TEXT | crm/lms/rms/rag/none |
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
| source_type | TEXT | crm/lms/rms/rag/none |
| query_text | TEXT | Original query |
| record_count | INTEGER | Number of records retrieved |
| payload | JSONB | Retrieved data |
| error_message | TEXT | Error if any |
| retrieval_time_ms | INTEGER | Retrieval time |
| created_at | TIMESTAMP | Creation time |

#### `rag_documents`
Stores knowledge base documents.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| file_name | TEXT | Document filename |
| content | TEXT | Document content |
| created_at | TIMESTAMP | Creation time |

#### `rag_embeddings`
Stores vector embeddings for documents.

| Column | Type | Description |
|--------|------|-------------|
| document_id | UUID | Foreign key to rag_documents |
| embedding | vector(3072) | OpenAI embedding vector |
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
- `leads`: Customer leads
- `tasks`: Task management
- `trainers`: Trainer information
- `learners`: Learner information
- `Course`: Course catalog
- `activity`: Activity logs
- `notes`: Notes and comments

#### LMS Tables
- `batches`: Training batches

#### RMS Tables
- `job_openings`: Job postings
- `candidates`: Candidate profiles
- `companies`: Company information
- `interviews`: Interview schedules
- `tasks`: Recruitment tasks

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
Send a chat message.

**Request:**
```json
{
  "message": "Show me all job openings",
  "session_id": "uuid"
}
```

**Response:**
```json
{
  "response": "Here are the job openings...",
  "session_id": "uuid"
}
```

### Health Check

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 📊 Data Sources

### CRM (Customer Relationship Management)

**Supported Tables:**
- `campaigns`: Marketing campaigns
- `leads`: Customer leads and prospects
- `tasks`: Task management
- `trainers`: Trainer profiles
- `learners`: Learner profiles
- `Course`: Course catalog
- `activity`: Activity logs
- `notes`: Notes and comments

**Query Examples:**
- "Show me all leads"
- "List trainers in New York"
- "What campaigns are active?"
- "Show me tasks due today"

**Features:**
- Automatic table detection based on keywords
- Date filtering (today, yesterday, this week, new)
- Text search across multiple fields
- Pagination support

### LMS (Learning Management System)

**Supported Tables:**
- `batches`: Training batches and schedules

**Query Examples:**
- "Show me all batches"
- "List upcoming training batches"
- "What batches are scheduled this week?"

**Features:**
- Batch schedule queries
- Date-based filtering
- Status filtering

### RMS (Recruitment Management System)

**Supported Tables:**
- `job_openings`: Job postings and openings
- `candidates`: Candidate profiles
- `companies`: Company information
- `interviews`: Interview schedules
- `tasks`: Recruitment tasks

**Query Examples:**
- "Show me all job openings"
- "List candidates in New York"
- "What companies do we have?"
- "Show interviews scheduled for today"
- "RMS tasks with high priority"

**Features:**
- Intelligent table detection
- Multi-field search
- Date filtering
- Status filtering

### RAG (Retrieval-Augmented Generation)

**Capabilities:**
- Vector similarity search
- Document retrieval
- Knowledge base queries

**Query Examples:**
- "What is the refund policy?"
- "How do I reset my password?"
- "Show me the user manual"

**Features:**
- Semantic search using embeddings
- Similarity threshold filtering
- Document content retrieval

## 🚢 Deployment

### Docker Deployment

The application is containerized and ready for deployment using Docker.

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

**Using a custom port:**
```bash
docker run -d \
  --name edify-chatbot \
  -p 8081:8081 \
  -e PORT=8081 \
  --env-file .env \
  edify-chatbot
```

**Using environment variables directly:**
```bash
docker run -d \
  --name edify-chatbot \
  -p 8080:8080 \
  -e PORT=8080 \
  -e OPENAI_API_KEY=your_key \
  -e EDIFY_SUPABASE_URL=your_url \
  -e EDIFY_SUPABASE_SERVICE_ROLE_KEY=your_key \
  -e CHATBOT_SUPABASE_URL=your_url \
  -e CHATBOT_SUPABASE_SERVICE_ROLE_KEY=your_key \
  edify-chatbot
```

> **Note:** The default port is **8080** to avoid conflicts with common ports 3000 and 8000. You can change it by setting the `PORT` environment variable.

#### Docker Compose (Recommended)

A `docker-compose.yml` file is already included. To use a custom port, set the `PORT` environment variable:

```bash
# Use default port 8080
docker-compose up -d

# Or use a custom port
PORT=8081 docker-compose up -d
```

You can also edit the `docker-compose.yml` file to change the port mapping directly.

#### Production Deployment

For production, consider:

1. **Use a reverse proxy** (nginx, Traefik) in front of the container
2. **Set up proper logging** with volume mounts
3. **Use Docker secrets** or a secrets management service
4. **Configure resource limits** in docker-compose or Kubernetes
5. **Set up health checks** and monitoring

Example with resource limits:
```yaml
services:
  chatbot:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    environment:
      - PORT=8080
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

#### Kubernetes Deployment

For Kubernetes, create deployment and service manifests:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edify-chatbot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: edify-chatbot
  template:
    metadata:
      labels:
        app: edify-chatbot
    spec:
      containers:
      - name: chatbot
        image: edify-chatbot:latest
        ports:
        - containerPort: 8080
        env:
        - name: PORT
          value: "8080"
        envFrom:
        - secretRef:
            name: edify-chatbot-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "1"
          limits:
            memory: "2Gi"
            cpu: "2"
---
apiVersion: v1
kind: Service
metadata:
  name: edify-chatbot-service
spec:
  selector:
    app: edify-chatbot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

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

### Adding a New Data Source

1. Create repository in `app/db/` (e.g., `new_source_repo.py`)
2. Create fetch node in `app/langgraph/nodes/` (e.g., `fetch_new_source.py`)
3. Add to `decide_source.py` keyword detection
4. Add node to `graph.py` workflow
5. Update `TABLE_CONFIGS` in repository

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

#### 3. Vector Search Not Working
- **Issue**: RPC function `match_documents` not found
- **Solution**: Run migration script to create RPC function

#### 4. Session Not Found
- **Issue**: Session ID not recognized
- **Solution**: Sessions are created automatically, ensure session_id is valid UUID

#### 5. No Data Returned
- **Issue**: Query returns empty results
- **Solution**: Check table names, field names, and data availability in Edify Supabase

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

