# Agent Governance Platform

## RAG chunking + vector DB

The agent orchestrator stores internal knowledge in PostgreSQL with the `pgvector`
extension. Text or Markdown files are split into overlapping chunks, embedded with
Ollama, and searched with vector similarity. If embeddings or the vector index are
not available, `knowledge.search` falls back to PostgreSQL full-text search.

### Local setup

```powershell
docker compose up -d postgres ollama
```

Pull an embedding model once:

```powershell
docker compose exec ollama ollama pull nomic-embed-text
```

Create/update database tables and the vector index:

```powershell
$env:PYTHONPATH='service/agent-orchestrator'
$env:POSTGRES_PORT='5433'
.\venv\Scripts\python.exe -m app.db.init_db
```

Ingest a document:

```powershell
$env:PYTHONPATH='service/agent-orchestrator'
$env:POSTGRES_PORT='5433'
.\venv\Scripts\python.exe -m app.rag.ingest_text service\agent-orchestrator\sample_knowledge\banking_process.md --document-type process
```

Use `--skip-embeddings` to ingest chunks without calling Ollama.

## Optional Supermemory Pipeline

Supermemory can be used as an external conversation memory layer. The local
PostgreSQL/pgvector RAG remains available for internal documents.

Enable it in `service/agent-orchestrator/.env`:

```env
SUPERMEMORY_ENABLED=true
SUPERMEMORY_API_KEY=sm_your_api_key_here
SUPERMEMORY_BASE_URL=https://api.supermemory.ai
SUPERMEMORY_TIMEOUT_SECONDS=15
SUPERMEMORY_CONTAINER_PREFIX=agent-governance
```

Send a stable `session_id` or `user_id` with each request:

```json
{
  "session_id": "session_001",
  "user_id": "employee_001",
  "input_text": "email cua khach hang do la gi?"
}
```

Pipeline:

```text
/api/v1/run
-> recall profile/relevant memories from Supermemory
-> run orchestrator and specialist agents with memory_context
-> store the user/assistant turn back into Supermemory
```

If `SUPERMEMORY_ENABLED=false` or the API key is missing, the pipeline falls back
to the local-only behavior.

## Auth Service

The auth service issues local JWT access tokens and refresh tokens backed by
PostgreSQL.

Run locally:

```powershell
cd D:\Python\agent-governance-platform
$env:PYTHONPATH='service/auth-service'
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

Or run with Docker Compose:

```powershell
docker compose up -d postgres auth-service
```

Register:

```http
POST http://localhost:8002/api/v1/auth/register
```

```json
{
  "email": "employee@example.com",
  "password": "Password123!",
  "full_name": "Employee One",
  "role": "employee",
  "scopes": ["agent:run", "customer:read"]
}
```

Main endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/introspect
```

Use the returned access token as:

```http
Authorization: Bearer <access_token>
```

## NGINX Edge Gateway

The project can run without the Python api-gateway for now:

```text
Client
-> NGINX
-> auth-service for register/login/token
-> NGINX auth_request verifies Bearer token through auth-service
-> agent-orchestrator
```

Run:

```powershell
docker compose up -d postgres auth-service agent-orchestrator nginx
```

Register/login through NGINX:

```http
POST http://localhost:8080/api/v1/auth/register
POST http://localhost:8080/api/v1/auth/login
```

Call the agent through NGINX:

```http
POST http://localhost:8080/api/v1/run
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "session_id": "session_001",
  "user_id": "employee_001",
  "input_text": "bao lau toi nhan duoc the"
}
```

NGINX verifies the token by calling:

```text
GET /api/v1/auth/verify
```

inside auth-service. If the token is valid, NGINX forwards user context headers:

```text
X-User-Id
X-User-Email
X-User-Role
X-User-Scopes
```

## Reference Resolution

Before routing to agents, the orchestrator resolves simple follow-up references
from memory context.

Example:

```text
Memory context:
- Assistant answered: Điện thoại của khách hàng John Smith là +84901111222.

New input:
email của khách hàng đó là gì?

Resolved input:
email của khách hàng John Smith là gì?
```

This happens in:

```text
app/memory/reference_resolver.py
```

and is called from:

```text
app/api.py
```
