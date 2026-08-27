# Backend — Sentinel MA

This is the FastAPI application powering Sentinel MA: agent orchestration,
the RAG pipeline, safety guardrails, medical imaging, voice, web search, and
every API route the frontend talks to. This document walks through every
file and folder in this directory. For the project as a whole (frontend,
data, the Colab notebook, root-level setup), see the
[main README](../README.md).

---

## Table of Contents

- [Directory Structure](#directory-structure)
- [`main.py`](#mainpy)
- [`agentic_systems/`](#agentic_systems)
- [`api/`](#api)
- [`config/`](#config)
- [`guardrail/`](#guardrail)
- [`imaging/`](#imaging)
- [`rag/`](#rag)
- [`web_search/`](#web_search)
- [`voice/`](#voice)
- [`utils/`](#utils)
- [How a Request Actually Flows](#how-a-request-actually-flows)

---

## Directory Structure

```text
backend/
├── agentic_systems/
│   ├── agents/
│   │   ├── imaging_analysis_agent.py
│   │   ├── rag_agent.py
│   │   ├── router_agent.py
│   │   └── web_search_agent.py
│   ├── orchestrator.py
│   └── state.py
├── api/
│   ├── database/
│   │   └── database.py
│   ├── models/
│   │   ├── db_models.py
│   │   └── schemas.py
│   └── routers/
│       ├── chat_router.py
│       ├── conversation_router.py
│       ├── imaging_router.py
│       └── voice_router.py
├── config/
│   ├── llm_clients.py
│   ├── prompts.py
│   └── settings.py
├── guardrail/
│   ├── input_guardrail.py
│   └── output_guardrail.py
├── imaging/
│   └── medgemma_client.py
├── rag/
│   ├── query_expansion.py
│   ├── relevance_checker.py
│   ├── reranker.py
│   └── retrievers.py
├── utils/
│   ├── conversation_helper.py
│   ├── exceptions.py
│   └── logger.py
├── voice/
│   ├── stt.py
│   └── tts.py
├── web_search/
│   ├── domains_to_search.py
│   └── exa_client.py
└── main.py
```

---

## `main.py`

The FastAPI application entrypoint. Responsible for:
- Constructing the `FastAPI` app instance and registering CORS middleware
  (so the separately-hosted frontend can call this API from another origin).
- Running startup tasks: creating the upload directory and ChromaDB
  persistence directory if they don't exist, and initializing the SQLite
  database schema.
- Registering a global exception handler that catches the project's typed
  exception hierarchy (`utils/exceptions.py`) and converts each one into a
  clean HTTP response instead of leaking a raw stack trace.
- Including every router from `api/routers/` (chat, conversation, imaging,
  voice) under the app.
- Mounting `data/uploads` as a static file server (`/media`), so uploaded
  images can be served back to the frontend by URL rather than by re-reading
  the file on every request.
- Exposing a simple `/api/health` endpoint for the frontend's connection
  status indicator.

This is the file you run (via `run.py` or `uvicorn main:app`) to start the
whole backend.

---

## `agentic_systems/`

The multi-agent orchestration layer, built on **LangGraph**. This is where
the actual "which agent handles this" decision-making and hand-off logic
lives — everything else in the backend (routers, RAG, guardrails) is a
building block that gets wired together here.

### `state.py`

Defines `AgentState`, the single `TypedDict` schema that every node in the
LangGraph workflow reads from and writes to. Think of it as the shared
whiteboard the whole multi-agent conversation is conducted on: the original
user query, chat history, which route was chosen, retrieved chunks, web
search results, image analysis findings, confidence scores, the final
answer, and source citations all live in one place with one consistent
shape. Because every agent node speaks the same state shape, adding or
reordering nodes in the graph doesn't require renegotiating data formats
between them.

### `orchestrator.py`

Builds and compiles the actual LangGraph `StateGraph`: registers every node
(input guardrail, router, RAG, web search, general chat, image analysis,
output guardrail), wires the conditional edges between them (e.g. "if the
input guardrail blocks the message, go straight to the blocked-response
node instead of the router"), and exposes a single `run_workflow(...)`
entrypoint that the API routers call to process one turn of conversation.
The compiled graph is built once and cached as a module-level singleton —
it's the same graph structure reused for every request; only the state
flowing through it is fresh per call.

This file also contains the "glue" nodes that don't warrant their own file
because they're small — the general-conversation handler, the
blocked-response handler, and the finalize step that merges whichever
agent's output should become the response.

### `agents/`

The individual specialist agents, each a plain function that takes
`AgentState` in and returns an updated `AgentState`, wired into the graph by
`orchestrator.py`.

**`router_agent.py`** — The entry-point classifier. Given the (contextualized)
user query, it uses a small/fast LLM call with a strictly-typed structured
output schema to decide whether the query should go to `rag`, `web_search`,
or `general`. If an image is attached to the message, routing is
deterministic — it goes straight to image analysis without spending an LLM
call on a decision that isn't actually ambiguous.

**`rag_agent.py`** — The retrieval-augmented generation pipeline: expands
the query with medical synonyms, retrieves candidate chunks from the hybrid
vector store, reranks them for precision, and runs a per-chunk relevance
check before generating an answer. Chunks that fail the relevance check are
replaced with live web search results rather than silently dropped; if
*nothing* retrieved is relevant, the whole query hands off to the web search
agent instead of generating an answer on weak grounding. Confidence is
computed as a blend of the model's own self-reported certainty and the
reranker's score for the top chunk.

**`web_search_agent.py`** — Runs a live Exa.ai search (restricted to
reputable medical/research domains — see `web_search/domains_to_search.py`)
and generates a cited answer from the results. Invoked either directly (the
router decided the query needs current information) or as a fallback when
the RAG agent's retrieval wasn't good enough.

**`imaging_analysis_agent.py`** — Wraps a call to the MedGemma client
(`imaging/medgemma_client.py`), passing the uploaded image and prompt, and
populates the state with the resulting findings and a confidence score
derived from the model's own generation. This is the one agent whose output
is *always* flagged for human review, unconditionally, regardless of the
confidence score it produced.

---

## `api/`

Everything that defines the actual HTTP surface of the backend: database
setup, request/response schemas, and the route handlers themselves.

### `database/database.py`

SQLAlchemy engine and session setup for the SQLite database. Defines the
declarative `Base` class every ORM model inherits from, a `get_db()`
dependency for FastAPI route handlers to receive a scoped database session,
and an `init_db()` function (called once at startup in `main.py`) that
creates any tables that don't already exist. Note: this only *creates*
missing tables — it does not alter existing ones, so a schema change (like
adding a new column) requires either deleting the existing SQLite file in
development or a real migration tool in production.

### `models/db_models.py`

The SQLAlchemy ORM models — the actual database schema:
- **`Conversation`** — one row per chat thread, with a title and creation
  timestamp.
- **`Message`** — one row per turn (user or assistant), storing its content,
  which agent produced it, its confidence score, its source citations, an
  optional attached image URL, and whether it's flagged for human review.
  This is also what makes conversation history — including previously
  uploaded images — reload correctly when switching between conversations.
- **`DocumentRecord`** — tracks uploaded images/documents on disk (filename,
  filepath, processing status).
- **`HumanReview`** — the audit log for the human-in-the-loop review
  feature: which message was reviewed, by whom, what decision was made
  (approved / edited / rejected), and any corrected content or notes.

### `models/schemas.py`

The Pydantic request/response models that define the API's actual contract
— what a `POST /api/chat` request body must look like, what a chat response
contains (answer, confidence, agent used, sources, whether it needs review),
what an image analysis response looks like, and so on. FastAPI uses these
both to validate incoming requests and to auto-generate the interactive API
docs at `/docs`.

### `routers/`

The actual endpoint handlers, one file per feature area:

**`chat_router.py`** — `POST /api/chat`, the main text-conversation
endpoint. Resolves or creates the target conversation, persists the user's
message, invokes the orchestrator's `run_workflow(...)`, persists the
assistant's response, and returns it.

**`imaging_router.py`** — `POST /api/imaging/upload`, handling image
uploads. Validates the file type, saves it to disk, creates a
`DocumentRecord`, and runs it through image analysis — persisting both the
user's message (with the image reference) and the assistant's findings to
the conversation, which is what makes uploaded images actually show up when
revisiting that conversation later rather than only existing for the
current browser session.

**`voice_router.py`** — `POST /api/voice/speech-to-text` and
`POST /api/voice/text-to-speech`, thin wrappers around the ElevenLabs
clients in `voice/`.

**`conversation_router.py`** — Conversation history endpoints: listing all
conversations, fetching a specific conversation's full message history
(including image URLs), and the human-review endpoints — listing pending
reviews and submitting a review decision.

---

## `config/`

Every piece of configuration in the entire backend — API keys, model names,
retrieval parameters, thresholds, and system prompts — lives here.
Nothing outside this folder should hardcode a model name, a `top_k`, or a
prompt string.

### `settings.py`

A single `pydantic-settings`-based `Settings` class, loaded from `.env` via
explicit `python-dotenv` loading. Every tunable value in the system is a
named field here: which LLM provider and model to use, retrieval `top_k`
and reranking cutoffs, the confidence threshold that triggers a RAG→web
handoff, MedGemma's generation parameters, ElevenLabs voice IDs, and so on.
A cached `get_settings()` function returns the singleton instance used
everywhere else.

### `llm_clients.py`

The single place LLM client objects get constructed — `get_chat_llm()` for
the main reasoning model and `get_guardrail_llm()` for the smaller/cheaper
model used by guardrails, relevance checking, and query expansion. Also
defines `invoke_structured()`, a shared helper that wraps
`.with_structured_output(...).invoke(...)` and normalizes the result to
always be the expected Pydantic model instance — since that call's return
type isn't perfectly uniform across every LangChain version/provider
combination, every structured-output call site in the codebase routes
through this helper rather than calling `with_structured_output` directly.

### `prompts.py`

Every system prompt used anywhere in the workflow, as named string
constants — the input and output guardrail prompts, the router's
classification prompt, the RAG and web search generation prompts, the
general-chat prompt, MedGemma's instruction, and the canned "blocked"
response text. Centralizing these means tuning an agent's behavior is a
one-file change, and no prompt text is duplicated or drifts between two
copies.

---

## `guardrail/`

Safety screening on both sides of every conversation turn.

**`input_guardrail.py`** — Screens the incoming query *before* any
retrieval, search, or generation happens, using a small LLM with a strictly
typed structured-output schema (`safe`/`reason`/`category`). Blocks requests
for self-harm instructions, prompt-injection attempts, and content entirely
unrelated to healthcare — while explicitly allowing short image-analysis
instructions ("analyze this image"), brief contextual follow-ups, and
sensitive-but-legitimate clinical questions. Fails open (defaults to
allowing the request) if the guardrail call itself errors, since a broken
guardrail should never be the reason a legitimate clinical question goes
unanswered.

**`output_guardrail.py`** — Reviews the *draft* answer before it's returned
to the user: softens unqualified diagnostic language into appropriately
hedged possibilities, and flags the answer for human review if it contains
a specific treatment/dosage recommendation. Fails safe on error — if the
guardrail call itself fails, the answer is flagged for review rather than
silently passed through unreviewed.

---

## `imaging/`

**`medgemma_client.py`** — The HTTP client for the MedGemma imaging model.
Talks to a **custom FastAPI server** (defined and run via
`serve_medgemma_colab.ipynb` at the project root) rather than an
OpenAI-compatible schema like vLLM would provide. This is a deliberate
choice: vLLM was tried first for MedGemma and hung indefinitely when loading
the model on a free-tier Colab T4 GPU, while loading it directly via
`transformers` (`AutoProcessor` + `AutoModelForImageTextToText`, the
pattern the model card itself documents) works reliably. So instead of
speaking OpenAI's chat-completions format, this client POSTs a small custom
JSON payload (base64 image, prompt, generation parameters) to a `/analyze`
endpoint and receives back `{"text": ..., "confidence": ...}` — where the
confidence value is computed server-side from the model's own generation
scores.

---

## `rag/`

The retrieval-augmented generation pipeline's building blocks — everything
`agentic_systems/agents/rag_agent.py` calls into.

**`retrievers.py`** — Builds and persists the hybrid retrieval stores: a
**Chroma** vector store (dense embeddings) and a pickled **BM25Retriever**
(sparse keyword search), combined via LangChain's `EnsembleRetriever`
(weighted Reciprocal Rank Fusion). On first run, this ingests the PubMed
knowledge base by downloading only as many raw dataset files as needed to
reach the configured row limit (not the entire multi-million-row corpus),
embeds each abstract as-is with no chunking (PubMed abstracts are already
short, self-contained units), and persists both stores to disk — so every
subsequent startup loads them directly instead of rebuilding.

**`reranker.py`** — Wraps a HuggingFace cross-encoder model that re-scores
retrieved candidates directly against the query for much higher precision
than vector similarity alone, trimming the candidate pool down before it
ever reaches the relevance checker or the generation step.

**`relevance_checker.py`** — The per-chunk anti-hallucination gate: a small
LLM, using a structured-output schema, judges every retrieved chunk
individually as relevant or not to the actual query — strictly, since a
chunk that's merely topically adjacent but cited as evidence is worse than
no citation at all. This is what triggers the web-search backfill for
individual chunks, and the full RAG→web handoff when nothing retrieved
holds up.

**`query_expansion.py`** — Expands the user's query with related medical
terminology (synonyms, abbreviations) before retrieval, so a casually
phrased question ("heart attack") can still match literature that uses
precise clinical terminology ("myocardial infarction").

---

## `web_search/`

**`exa_client.py`** — The Exa.ai web search client, used both as the
router's direct web-search path and as the RAG agent's backfill mechanism
for chunks that fail the relevance check.

**`domains_to_search.py`** — The allowlist of reputable medical/research
domains (PubMed, WHO, CDC, NEJM, The Lancet, JAMA, Mayo Clinic, UpToDate,
Cochrane Library, and similar) that web searches are biased toward, so
results lean toward authoritative sources rather than arbitrary web content.

---

## `voice/`

**`stt.py`** — Speech-to-text via ElevenLabs' Scribe model: accepts an
uploaded audio blob and returns the transcribed text.

**`tts.py`** — Text-to-speech via ElevenLabs' Flash model: accepts text and
returns synthesized audio, used by the frontend's per-message play/pause/stop
controls (the audio is fetched once and cached client-side, not re-fetched
on every playback control interaction).

---

## `utils/`

Small, shared building blocks used across multiple other modules.

**`logger.py`** — Central `loguru` configuration, writing to both the
console and a rotating log file. Every other module imports its logger from
here rather than configuring logging independently.

**`exceptions.py`** — The typed exception hierarchy (e.g. `RetrievalError`,
`ImageAnalysisError`, `WebSearchError`, `VoiceProcessingError`,
`GuardrailViolationError`) that lets the global exception handler in
`main.py` translate internal failures into clean, predictable HTTP
responses instead of leaking raw stack traces to the frontend.

**`conversation_helper.py`** — Shared logic used by both `chat_router.py`
and `imaging_router.py` to avoid duplicating it: getting-or-creating a
conversation by ID, and converting an on-disk image filepath into the
servable `/media/...` URL the frontend actually needs to display it.

---

## How a Request Actually Flows
<img width="2720" height="2440" alt="sentinel_ma_technical_workflow" src="https://github.com/user-attachments/assets/f6157cf6-e26d-41e2-ba0c-352e35c47db1" />

Tying the above together, a text question sent to `POST /api/chat`:

1. `api/routers/chat_router.py` resolves/creates the conversation via
   `utils/conversation_helper.py`, saves the user's message, and calls
   `agentic_systems/orchestrator.py`'s `run_workflow(...)`.
2. The graph runs: `guardrail/input_guardrail.py` screens the query →
   `agentic_systems/agents/router_agent.py` classifies it → the chosen agent
   (`rag_agent.py`, `web_search_agent.py`, or the orchestrator's own
   general-chat node) produces a draft answer, pulling from `rag/` and
   `web_search/` as needed → `guardrail/output_guardrail.py` reviews the
   draft.
3. `chat_router.py` persists the assistant's message (via
   `api/models/db_models.py`) and returns it, shaped by
   `api/models/schemas.py`.

An uploaded image follows the same shape through `imaging_router.py`, except
routing is deterministic straight to `imaging_analysis_agent.py` →
`imaging/medgemma_client.py`, and the result is *always* flagged for human
review regardless of confidence.
