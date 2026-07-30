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
