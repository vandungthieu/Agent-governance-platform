# Agent Governance Platform

Agent Governance Platform is a production-oriented backend platform for building governed multi-agent AI assistants in enterprise environments.

Instead of being a simple chatbot wrapper around an LLM, this project focuses on the backend concerns required to run AI agents safely and observably: authentication, role-aware access, RAG over internal documents, long-term memory, request tracing, tool execution, vector search, and gateway-level token verification.

The current domain is banking operations, but the architecture is intentionally modular so the same foundation can be reused for other business domains.

## Why This Project Matters

Most AI chatbot demos stop at prompt engineering. This project explores what is needed around the model to make an AI assistant useful in a real organization:

- Requests are authenticated before reaching internal agents.
- User roles and scopes can be enforced through an auth layer.
- Agents retrieve trusted knowledge from internal documents instead of relying only on model memory.
- Customer data and public banking knowledge are handled through separate agent workflows.
- Simple structured lookups can bypass the LLM for faster and more deterministic answers.
- Every workflow step, model call, and tool call can be traced for debugging and audit.
- The backend can be exposed through real channels such as web apps, Telegram, or Zalo.

## System Flow

```text
Client / Chat Channel
        |
        v
      NGINX
        |
        +--> Auth Service
        |       |
        |       +--> JWT / roles / scopes
        |
        v
 Agent Orchestrator
        |
        +--> Banking Knowledge Agent
        |       +--> RAG / PostgreSQL / pgvector
        |
        +--> Customer Data Agent
        |       +--> Direct parser / structured lookup
        |
        +--> Memory Layer
        |       +--> Supermemory
        |
        +--> Ollama
                +--> chat model / embedding model
```

Typical request lifecycle:

```text
Client sends input
-> NGINX verifies access token through auth-service
-> agent-orchestrator recalls memory context
-> reference resolver rewrites follow-up questions when needed
-> hybrid intent router classifies and routes the task
-> specialist agent retrieves knowledge or parses structured data
-> LLM is called only when generation or reasoning is needed
-> telemetry is stored
-> final answer is returned
```

## Key Engineering Highlights

- Designed a modular multi-service backend with clear service boundaries.
- Implemented JWT-based authentication with access tokens, refresh tokens, roles, and scopes.
- Replaced the temporary Python API gateway with NGINX `auth_request` token verification.
- Built a RAG pipeline with Markdown chunking, Ollama embeddings, PostgreSQL, and pgvector.
- Added vector search with lexical reranking for Vietnamese banking knowledge.
- Upgraded routing from keyword-only rules to hybrid intent routing with semantic examples, rule fallback, and LLM planner fallback for ambiguous requests.
- Implemented fast-path parsers for structured customer-data and FAQ lookups to reduce unnecessary LLM calls.
- Integrated optional long-term memory through Supermemory.
- Added reference resolution so follow-up questions like "email của khách hàng đó là gì?" can be resolved from memory context.
- Added telemetry tables for request tracing, workflow timing, model calls, and tool calls.
- Containerized the main services with Docker Compose.

## Core Features

- Multi-agent orchestration for banking knowledge and customer-data workflows.
- Hybrid intent routing with high-confidence rules, semantic examples, and LLM planner fallback.
- Auth service for employee login, token issuing, token verification, and user context.
- NGINX edge gateway for protected internal APIs.
- RAG over internal Markdown documents.
- PostgreSQL/pgvector vector database for semantic retrieval.
- Ollama integration for local chat and embedding models.
- Supermemory integration for optional long-term conversation memory.
- Deterministic direct lookup path for known structured questions.
- Telemetry and audit-friendly traces for debugging slow or incorrect requests.
- Adapter-friendly backend design for web, Telegram, Zalo, or mobile clients.
- Telegram webhook adapter for routing chat messages into the agent workflow.

## Example Use Cases

### Banking FAQ

```text
User:
bao lâu tôi nhận được thẻ?

System:
routes to BankingKnowledgeAgent
-> retrieves the matching FAQ chunk
-> returns the answer from internal knowledge
```

### Customer Data Lookup

```text
User:
số điện thoại của khách hàng John Smith

System:
routes to CustomerDataAgent
-> reconstructs the customer profile section
-> parses the Điện thoại field
-> returns the exact value without calling the LLM
```

### Follow-Up With Memory

```text
User:
số điện thoại của John Smith?

User:
email của khách hàng đó là gì?

System:
uses memory context
-> resolves "khách hàng đó" to "John Smith"
-> runs the correct customer-data workflow
```

## Main Components

### NGINX

Acts as the edge gateway:

- Proxies public auth endpoints to auth-service.
- Verifies Bearer tokens through auth-service.
- Forwards valid requests to agent-orchestrator.

### Auth Service

Handles identity and access:

- Register and login.
- Access token and refresh token issuing.
- Token verification and introspection.
- Role and scope management.

### Agent Orchestrator

Coordinates the AI workflow:

- Receives authenticated user requests.
- Recalls memory context.
- Resolves follow-up references.
- Classifies and routes tasks.
- Calls specialist agents, tools, RAG, direct parsers, or LLMs.
- Stores telemetry for each request.

### Specialist Agents

Current agents:

- `BankingKnowledgeAgent`: answers questions about banking processes, public references, FAQs, and product knowledge.
- `CustomerDataGuardAgent`: handles customer profile questions and structured customer-data lookup.

### RAG And Vector DB

Internal documents are processed through:

```text
Markdown document
-> chunking
-> embedding with Ollama
-> PostgreSQL/pgvector storage
-> semantic retrieval during agent execution
```

### Memory

Memory helps the assistant handle multi-turn conversations:

```text
User: số điện thoại của John Smith?
Bot: ...

User: email của khách hàng đó là gì?
```

The reference resolver can rewrite the second question into:

```text
email của khách hàng John Smith là gì?
```

## Tech Stack

- Python
- FastAPI
- LangGraph
- PostgreSQL
- pgvector
- SQLAlchemy
- Ollama
- Supermemory
- NGINX
- Docker Compose

## Project Structure

```text
service/
  auth-service/             Authentication and token management
  agent-orchestrator/       Multi-agent workflow, RAG, memory, telemetry
  telegram-adapter/         Telegram webhook adapter for chat integration
  api-gateway/              Earlier Python gateway, currently replaceable by NGINX
  audit-service/            Future production audit boundary
  guardrail-service/        Future production guardrail boundary

infra/
  nginx/                    NGINX gateway configuration

docs/
  architecture.md           Technical architecture and runbook
```

## Technical Documentation

Detailed setup commands, Docker Compose configuration, ports, database tables, RAG ingest commands, Supermemory settings, and telemetry SQL are documented in:

```text
docs/architecture.md
```
