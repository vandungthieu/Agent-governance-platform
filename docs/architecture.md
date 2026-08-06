# Architecture

Tài liệu này mô tả chi tiết kỹ thuật của Agent Governance Platform: cấu trúc dịch vụ, luồng request, cấu hình Docker, RAG, memory, auth và các lệnh vận hành.

## Service Boundaries

```text
Client / Channel Adapter
-> NGINX
-> auth-service
-> telegram-adapter optional
-> agent-orchestrator
-> PostgreSQL/pgvector
-> Ollama
-> Supermemory optional
```

### `service/auth-service`

Chịu trách nhiệm xác thực và phân quyền nền tảng:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/verify`
- `POST /api/v1/auth/introspect`

Bảng dữ liệu:

- `auth_users`
- `auth_refresh_tokens`

### `service/agent-orchestrator`

Chịu trách nhiệm chạy workflow multi-agent:

- Route request.
- Recall memory.
- Resolve reference.
- Retrieve knowledge.
- Gọi specialist agents.
- Ghi telemetry.

Endpoint chính:

- `GET /api/v1/health`
- `GET /api/v1/tools`
- `GET /api/v1/db/health`
- `POST /api/v1/run`

### `infra/nginx`

NGINX làm edge gateway:

- Public auth endpoints được proxy tới auth-service.
- Telegram webhook được proxy tới telegram-adapter.
- Protected agent endpoints dùng `auth_request` tới `/api/v1/auth/verify`.
- Request hợp lệ được forward tới agent-orchestrator.

### `service/telegram-adapter`

Chịu trách nhiệm tích hợp Telegram Bot API với workflow nội bộ:

- Nhận webhook từ Telegram tại `POST /telegram/webhook`.
- Parse `chat_id`, Telegram `user_id` và `message.text`.
- Map sang schema nội bộ của agent:

```json
{
  "session_id": "telegram:<chat_id>",
  "user_id": "telegram:<telegram_user_id>",
  "input_text": "..."
}
```

- Gọi `agent-orchestrator`.
- Gửi `final_answer` về Telegram bằng Bot API `sendMessage`.

## Ports

Từ máy host Windows:

```text
localhost:5432 -> PostgreSQL local trên máy
localhost:5433 -> PostgreSQL Docker pgvector
localhost:8001 -> agent-orchestrator trực tiếp
localhost:8002 -> auth-service trực tiếp
localhost:8003 -> telegram-adapter trực tiếp
localhost:8088 -> NGINX edge gateway
localhost:11434 -> Ollama host/container exposed port
```

Từ container trong Docker network:

```text
postgres:5432
auth-service:8000
agent-orchestrator:8000
telegram-adapter:8000
ollama:11434
```

## Docker Compose

Chạy hạ tầng chính:

```powershell
cd D:\Python\agent-governance-platform
$env:POSTGRES_PASSWORD='<local-postgres-password>'
$env:JWT_SECRET_KEY='<local-jwt-secret-at-least-32-chars>'
$env:TELEGRAM_BOT_TOKEN='<bot-token-if-using-telegram>'
docker compose up -d postgres auth-service agent-orchestrator telegram-adapter nginx
```

`POSTGRES_PASSWORD` và `JWT_SECRET_KEY` là bắt buộc khi chạy Docker Compose. Các giá trị nhạy cảm này nên được set trong PowerShell hoặc file `.env` ở root dự án, không hard-code trong `docker-compose.yml`.

Nếu dùng Ollama container:

```powershell
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:7b-instruct
docker compose exec ollama ollama pull nomic-embed-text
```

Nếu dùng Ollama cài trên host, agent-orchestrator trong Docker dùng:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Nếu dùng Ollama container, đổi thành:

```env
OLLAMA_BASE_URL=http://ollama:11434
```

## Auth Flow Qua NGINX

```text
Client
-> POST /api/v1/auth/login
-> NGINX
-> auth-service
-> access_token
```

Sau đó client gọi agent:

```http
POST http://localhost:8088/api/v1/run
Authorization: Bearer <access_token>
Content-Type: application/json
```

NGINX verify token bằng subrequest:

```text
GET /api/v1/auth/verify
```

Nếu hợp lệ, NGINX forward các headers:

```text
X-User-Id
X-User-Email
X-User-Role
X-User-Scopes
```

## Auth Service

Chạy local:

```powershell
cd D:\Python\agent-governance-platform
$env:PYTHONPATH='service/auth-service'
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

Chạy bằng Docker:

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

Login:

```http
POST http://localhost:8002/api/v1/auth/login
```

Use token:

```http
Authorization: Bearer <access_token>
```

## Agent Orchestrator

Chạy local:

```powershell
cd D:\Python\agent-governance-platform
$env:PYTHONPATH='service/agent-orchestrator'
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

Chạy bằng Docker:

```powershell
docker compose up -d postgres agent-orchestrator
```

Request trực tiếp:

```http
POST http://localhost:8001/api/v1/run
Content-Type: application/json
```

```json
{
  "session_id": "session_001",
  "user_id": "employee_001",
  "input_text": "bao lau toi nhan duoc the"
}
```

Request qua NGINX:

```http
POST http://localhost:8088/api/v1/run
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Telegram Adapter

Tạo bot bằng `@BotFather`, sau đó cấu hình token qua biến môi trường:

```powershell
$env:TELEGRAM_BOT_TOKEN='<bot-token>'
docker compose up -d --build telegram-adapter nginx
```

Webhook public qua NGINX:

```http
POST http://localhost:8088/telegram/webhook
```

Khi test local với Telegram thật, cần một public HTTPS URL, ví dụ bằng ngrok:

```powershell
ngrok http 8088
```

Set webhook:

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<ngrok-domain>/telegram/webhook
```

Nếu dùng `TELEGRAM_WEBHOOK_SECRET`, set webhook kèm `secret_token` và adapter sẽ kiểm tra header:

```text
X-Telegram-Bot-Api-Secret-Token
```

## RAG Chunking And Vector DB

PostgreSQL Docker dùng image:

```text
pgvector/pgvector:pg16
```

Tài liệu được lưu trong:

- `knowledge_documents`
- `knowledge_chunks`

Mỗi chunk có:

- `content`
- `embedding vector(768)`
- `chunk_index`
- `document_id`

Khởi tạo DB:

```powershell
cd D:\Python\agent-governance-platform
$env:PYTHONPATH='service/agent-orchestrator'
$env:POSTGRES_PORT='5433'
.\venv\Scripts\python.exe -m app.db.init_db
```

Ingest tài liệu:

```powershell
$env:PYTHONPATH='service/agent-orchestrator'
$env:POSTGRES_PORT='5433'
.\venv\Scripts\python.exe -m app.rag.ingest_text service\agent-orchestrator\sample_knowledge\account_opening.md --document-type banking_faq --source-uri "MB public website"
```

Recommended document types:

```text
owner.md -> owner_profile
account_opening.md -> banking_faq
banking_process.md -> process
customer data files -> customer_profile
policy files -> policy
```

If `--document-type` is omitted, `ingest_text` infers common types from the file name.

Ingest không tạo embedding:

```powershell
.\venv\Scripts\python.exe -m app.rag.ingest_text <file.md> --skip-embeddings
```

Kiểm tra chunks:

```sql
SELECT
  kd.title,
  kd.document_type,
  count(kc.id) AS total_chunks,
  count(kc.embedding) AS chunks_with_embedding
FROM knowledge_documents kd
JOIN knowledge_chunks kc ON kc.document_id = kd.id
GROUP BY kd.title, kd.document_type;
```

Kiểm tra vector dimension:

```sql
SELECT vector_dims(embedding)
FROM knowledge_chunks
WHERE embedding IS NOT NULL
LIMIT 1;
```

## Retrieval Flow

```text
input_text
-> memory reference resolution
-> hybrid intent router
-> route + task_type + document_type
-> Ollama /api/embed
-> query vector
-> PostgreSQL pgvector cosine search
-> lexical rerank tiếng Việt không dấu
-> top chunks
-> agent
```

Vector search dùng toán tử pgvector:

```sql
ORDER BY kc.embedding <=> CAST(:query_embedding AS vector)
```

`kc` là alias SQL của bảng `knowledge_chunks`; `kd` là alias của `knowledge_documents`.

## Hybrid Intent Routing

Routing flow:

```text
input_text
-> high-confidence deterministic rules
-> semantic intent router using embedding examples
-> LLM planner fallback for ambiguous requests
-> keyword fallback if semantic/planner routing is unavailable
```

Main intents:

```text
customer_lookup
masking_request
banking_faq
owner_question
realtime_web
document_intelligence
research_report
credit_risk
smalltalk
unknown
```

The router returns `intent`, `route`, `task_type`, `document_type`, `confidence`, and `routing_source`. `document_type` is used as a retrieval filter, for example:

```text
owner_question -> owner_profile
banking_faq -> banking_faq
customer_lookup -> customer_profile
```

## Direct Answer Fast Path

Không phải câu nào cũng cần LLM. Với lookup có cấu trúc, agent ưu tiên parse trực tiếp:

```text
số điện thoại của khách hàng John Smith
-> reconstruct customer section
-> parse markdown row Điện thoại
-> return answer
```

Các field đang hỗ trợ:

- Điện thoại
- Email
- Địa chỉ
- Số tài khoản
- Ngày sinh/năm sinh
- Trạng thái
- Phân hạng

FAQ đơn giản cũng có fast path:

```text
bao lâu tôi nhận được thẻ
-> tìm heading FAQ phù hợp
-> trả đoạn trả lời đầu tiên
```

## Supermemory Pipeline

Enable trong `service/agent-orchestrator/.env`:

```env
SUPERMEMORY_ENABLED=true
SUPERMEMORY_API_KEY=sm_your_api_key_here
SUPERMEMORY_BASE_URL=https://api.supermemory.ai
SUPERMEMORY_TIMEOUT_SECONDS=15
SUPERMEMORY_CONTAINER_PREFIX=agent-governance
```

Pipeline:

```text
/api/v1/run
-> recall profile/relevant memories from Supermemory
-> resolve references from memory_context
-> run orchestrator and specialist agents
-> store user/assistant turn back into Supermemory
```

Nếu `SUPERMEMORY_ENABLED=false` hoặc thiếu API key, hệ thống chạy local-only.

## Reference Resolution

File:

```text
service/agent-orchestrator/app/memory/reference_resolver.py
```

Ví dụ:

```text
Memory context:
- Assistant answered: Điện thoại của khách hàng John Smith là +84901111222.

New input:
email của khách hàng đó là gì?

Resolved input:
email của khách hàng John Smith là gì?
```

## Telemetry

Các bảng telemetry:

- `agent_runs`
- `workflow_steps`
- `model_calls`
- `tool_calls`

Tổng thời gian request:

```sql
SELECT
  trace_id,
  route,
  task_type,
  intent,
  intent_confidence,
  routing_source,
  retrieval_document_type,
  routing_reason,
  matched_example,
  semantic_candidates,
  llm_planner_output,
  status,
  round(duration_ms::numeric, 2) AS duration_ms,
  started_at,
  finished_at
FROM agent_runs
ORDER BY started_at DESC
LIMIT 20;
```

Từng bước workflow:

```sql
SELECT
  step_name,
  agent_role,
  task_type,
  status,
  round(duration_ms::numeric, 2) AS duration_ms
FROM workflow_steps ws
JOIN agent_runs ar ON ar.id = ws.agent_run_id
WHERE ar.trace_id = 'tr_xxx'
ORDER BY ws.started_at;
```

Model calls:

```sql
SELECT
  agent_role,
  provider,
  model_name,
  status,
  round(duration_ms::numeric, 2) AS duration_ms,
  error_message
FROM model_calls mc
JOIN agent_runs ar ON ar.id = mc.agent_run_id
WHERE ar.trace_id = 'tr_xxx'
ORDER BY mc.created_at;
```

Tool calls:

```sql
SELECT
  tool_name,
  status,
  round(duration_ms::numeric, 2) AS duration_ms,
  error_message
FROM tool_calls tc
JOIN agent_runs ar ON ar.id = tc.agent_run_id
WHERE ar.trace_id = 'tr_xxx'
ORDER BY tc.created_at;
```

## Notes

- `api-gateway` Python đang tạm chưa cần dùng khi NGINX đóng vai trò edge gateway.
- `guardrail-service` và `audit-service` có thể giữ lại cho production governance layer.
- Không đóng gói model Ollama vào image app. Model nên nằm ở Ollama host/container và volume riêng.
