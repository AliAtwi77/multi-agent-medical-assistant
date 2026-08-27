<div align="center">

<h1>Sentinel MA — Multi-Agent Medical Assistant</h1>

[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/langgraph)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/)
[![Anthropic Claude](https://img.shields.io/badge/Anthropic_Claude-D97706?style=for-the-badge&logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![Google MedGemma](https://img.shields.io/badge/Google_MedGemma-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://huggingface.co/google/medgemma-1.5-4b-it)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs_Voice-000000?style=for-the-badge&logo=elevenlabs&logoColor=white)](https://elevenlabs.io/)
[![HuggingFace](https://img.shields.io/badge/Hugging_Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6600?style=for-the-badge&logo=chromadb&logoColor=white)](https://www.trychroma.com/)
[![PubMedBERT](https://img.shields.io/badge/PubMedBERT-023047?style=for-the-badge&logo=pubmed&logoColor=white)](https://huggingface.co/NeuML/pubmedbert-base-embeddings)
[![Exa.ai](https://img.shields.io/badge/Exa.ai_Search-000000?style=for-the-badge&logo=exa&logoColor=white)](https://exa.ai/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)

</div>

> A clinician asks a question. Behind the scenes, four specialized AI agents
> decide — in real time — whether the answer lives in a curated medical
> knowledge base, needs a live web search for something too recent to be
> indexed anywhere, requires reading an actual medical image, or is just a
> quick conversational reply. No single model tries to do everything. No
> answer ships without a clear line of sight to its sources.

## The Problem

Healthcare professionals increasingly reach for AI assistants to speed up
research, triage questions, and get a second pair of eyes on a scan — but
most general-purpose chat assistants have three structural weaknesses in a
clinical context:

1. **No grounding.** A model answering purely from memory can hallucinate a
   drug interaction or a dosage with total confidence, leaving no audit trail.
2. **No awareness of limits.** A single model doesn't know when its internal 
   knowledge is stale or insufficient — it generates an answer regardless.
3. **No accountability loop.** Nothing forces a human clinician to actually
   confirm an AI-generated finding before it's treated as usable.

## The Solution

Sentinel MA directly addresses these three failure modes:

* **Evidence Grounding:** Every text answer is grounded in retrieved context (via internal knowledge bases or live web search) complete with visible source citations.
* **Adaptive Fallback:** A chunk-level confidence system detects when internal knowledge is insufficient and automatically triggers live search routing.
* **Human-in-the-Loop Safeguards:** Every medical image analysis is conditionally flagged and queued for review by a licensed clinician before final approval.

---

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Features](#features)
- [Tools and Frameworks](#tools-and-frameworks)
- [Architecture](#architecture)
- [Pipeline](#pipeline)
- [Project Structure](#project-structure)
- [Root Folder Breakdown](#root-folder-breakdown)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [Using the Application](#using-the-application)
- [API and Token References](#api-and-token-references)
- [Logging](#logging)
- [Limitations](#limitations)

---

## What This Project Does

Sentinel MA is a full-stack, multi-agent clinical decision-support system. A
healthcare professional can type a clinical question, speak it out loud,
upload a medical image for analysis, or just make small talk — and the
system automatically figures out which specialized agent (or combination of
agents) should handle it, without the user ever having to pick a "mode."

Every text-based answer is grounded in either a pre-loaded medical knowledge
base or live web search (never both left unverified — a per-chunk relevance
check silently swaps out anything that isn't actually useful for a targeted
web search instead of just answering from weak context). Every image
analysis is queued, without exception, for human clinician sign-off before
it's treated as usable. Nothing about this system is meant to replace a
clinician's judgment — it's built to make evidence-gathering and triage
faster while keeping a human explicitly in the loop wherever it matters.

## Features

**🧠 Retrieval-Augmented Generation (RAG)**
Questions answerable from established medical literature are answered from a
pre-loaded corpus of 10,000 PubMed abstracts, retrieved via a hybrid dense +
sparse search, reranked for precision, and checked chunk-by-chunk for actual
relevance before ever reaching the model that writes the answer. Any chunk
that doesn't hold up is silently replaced with a live web search result
instead of just being dropped — so a gap in the internal corpus (a very new
drug, a disease not yet well-documented) doesn't just fail quietly.

**🌐 Real-Time Web Search**
Questions that need current information — the latest research, a recently
approved drug, breaking guideline updates — are answered from a live web
search biased toward reputable medical/research domains (PubMed, WHO, CDC,
NEJM, The Lancet, JAMA, Mayo Clinic, and more), with every claim cited back
to its source.

**🩻 Medical Imaging Analysis**
Uploaded medical images are analyzed by a vision-language model and always,
unconditionally, flagged for human clinician review before the findings are
treated as usable — imaging is the one place in this system where automatic
trust is never assumed.

**💬 General Conversation**
Greetings, small talk, and simple conversational exchanges that don't need
retrieval at all are handled directly and efficiently, without invoking the
heavier RAG or search pipelines for questions that don't need them.

**🛡️ Safety Guardrails on Every Turn**
Every message is screened before it's processed and every answer is
reviewed before it's returned — checking for unsafe requests going in, and
softening unqualified diagnostic language or flagging treatment
recommendations for clinician confirmation going out.

**🗣️ Voice In, Voice Out**
Speak a question instead of typing it, and listen to any answer read back —
with real play/pause/stop controls, not a one-shot "play once" button.

**👩‍⚕️ Human-in-the-Loop Review**
Every answer flagged as needing clinician sign-off (low confidence, or an
image analysis) lands in a dedicated review queue, where a clinician can
approve, edit-and-approve, or reject it — creating an auditable record of
who confirmed what.

## Tools and Frameworks

| Category | Choice | Why |
|---|---|---|
| Agent orchestration | **LangGraph** | Structured, inspectable multi-agent graph workflow instead of ad-hoc branching logic |
| LLM framework | **LangChain** | Unified interface across model providers, structured output, retriever abstractions |
| Chat / reasoning LLM | **Anthropic Claude** (or OpenAI, configurable) | Main reasoning engine for routing, generation, and guardrails |
| Medical imaging | **Google MedGemma** (via `transformers`) | Vision-language model for medical image analysis, served through a custom FastAPI wrapper (see [`serve_medgemma_colab.ipynb`](#root-folder-breakdown)) rather than vLLM — MedGemma was found to hang indefinitely under vLLM on a free-tier T4 GPU, while a direct `transformers` load works reliably |
| Vector database | **ChromaDB** | Embedded, disk-persisted vector store — no separate server process, no RAM ceiling |
| Sparse retrieval | **BM25** (via `rank_bm25` / LangChain's `BM25Retriever`) | Keyword-precise retrieval, fused with dense search |
| Hybrid retrieval fusion | **LangChain `EnsembleRetriever`** | Weighted Reciprocal Rank Fusion between dense and sparse retrievers |
| Embeddings | **PubMedBERT-based model** (`NeuML/pubmedbert-base-embeddings`) | Domain-specific medical embeddings, meaningfully better than general-purpose models for clinical text |
| Reranking | **HuggingFace cross-encoder** (`ms-marco-MiniLM`) | Precision reranking pass after hybrid retrieval |
| Web search | **Exa.ai** | Real-time search API, domain-filterable toward reputable medical sources |
| Speech-to-text / text-to-speech | **ElevenLabs** | Voice input transcription and voice output synthesis |
| Backend framework | **FastAPI** | Async Python API framework, typed request/response schemas |
| Database | **SQLite** (via SQLAlchemy) | Conversation history, human review audit log |
| Config management | **pydantic-settings + python-dotenv** | Typed, validated configuration loaded from environment variables |
| Frontend | **Vanilla HTML/CSS/JS** | No build step, fully decoupled from the backend, talks only via HTTP |

## Architecture

```
                         ┌──────────────────────────┐
                         │   Frontend (HTML/JS)       │  <- talks only via HTTP
                         └─────────────┬─────────────┘
                                       │ REST (JSON / multipart)
                         ┌─────────────▼─────────────┐
                         │   FastAPI backend           │
                         └─────────────┬─────────────┘
                                       │
       ┌───────────────┬──────────────┼──────────────┬───────────────┐
       ▼                ▼              ▼              ▼               ▼
 Input Guardrail   Router Agent    RAG Agent     Web Search Agent  Image Agent
 (small LLM)       (LangGraph)    (ChromaDB       (Exa.ai)         (MedGemma via
                                   hybrid +                        transformers,
                                   relevance                       custom FastAPI
                                   check)                          server)
       │                                                 │
       └────────────────────► Output Guardrail ◄─────────┘
                                     │
                       Relevance / confidence low?
                       RAG → Web Search handoff or
                       per-chunk web backfill
                                     │
                             Human-in-the-loop
                              review queue (SQLite)
```

A router agent classifies every incoming text query into one of three paths
— **RAG**, **web search**, or **general conversation** — while an uploaded
image is routed to the **image analysis** agent directly and deterministically
(there's no ambiguity to resolve once an image is attached, so no LLM
classification call is spent on it). All four paths converge back through an
output guardrail before the response reaches the user.

## Pipeline

**Text query, end to end:**

1. **Input guardrail** — a small, fast LLM screens the raw query for safety
   before anything else happens.
2. **Router** — classifies the query as `rag`, `web_search`, or `general`.
3a. **RAG path** — the query is expanded with medical synonyms, searched
   against the knowledge base via hybrid (dense + sparse) retrieval,
   reranked, and every surviving chunk is individually checked for actual
   relevance. Irrelevant chunks are silently replaced with live web search
   results; if *nothing* retrieved is relevant, the whole query hands off to
   web search instead of answering on weak grounding.
3b. **Web search path** — Exa.ai search restricted to reputable medical
   domains, with every claim in the answer cited back to its source.
3c. **General path** — handled directly by the chat model, using recent
   conversation history for context.
4. **Output guardrail** — the draft answer is reviewed for unqualified
   diagnostic language (softened if found) and flagged for human review if
   warranted.
5. **Response returned**, along with its confidence score, which agent
   produced it, its sources (if any), and whether it needs clinician review.

**Image analysis, end to end:**

1. Image uploaded → validated → saved.
2. MedGemma (served via the custom `transformers`-based FastAPI server)
   analyzes the image against the accompanying prompt.
3. The finding is **always** flagged for human review — no confidence
   threshold exempts imaging from this.
4. The clinician reviews, and either approves, edits-and-approves, or
   rejects it from the review queue.

## Project Structure

```text
my-project/
├── backend/                     # FastAPI application — see backend/README.md for a full breakdown
├── data/                        # SQLite DB, ChromaDB vector store, uploaded images (gitignored contents)
├── frontend/                    # Static HTML/CSS/JS UI — no build step, talks to the backend via HTTP
├── scripts/                     # Standalone utility scripts (e.g. knowledge-base ingestion)
├── .env                         # Environment variables / secrets (gitignored — see .env.example)
├── requirements.txt             # Python dependencies for the backend
├── run.py                       # Convenience launcher for the backend (uvicorn entrypoint)
└── serve_medgemma_colab.ipynb   # Colab notebook: serves MedGemma on a free T4 GPU via a custom FastAPI server
```

The `backend/` directory is intentionally documented separately — it's large
enough (agents, RAG pipeline, guardrails, routers, config) to deserve its own
file-by-file breakdown. See **[`backend/README.md`](./backend/README.md)**.

## Root Folder Breakdown

| Path | Purpose |
|---|---|
| `backend/` | The FastAPI application: agent orchestration, RAG pipeline, guardrails, API routers, imaging/voice/web-search clients, and configuration. Fully documented in its own README. |
| `data/` | Runtime data directory: the SQLite database file (conversation history, human review audit log), the persisted ChromaDB vector store + pickled BM25 index, and uploaded image files. Everything under here is generated at runtime and gitignored — nothing here should be committed. |
| `frontend/` | The single-page web UI (plain HTML/CSS/JS, no build tooling). Talks to the backend exclusively over HTTP, configurable via a single base-URL constant, so it can be deployed independently of the backend. |
| `scripts/` | Standalone, runnable Python scripts that aren't part of the live API — most notably the knowledge-base ingestion script that seeds the PubMed corpus into ChromaDB/BM25 ahead of time, so the app never has to do that work on a live request. |
| `.env` | Your actual environment variables and API keys — **never commit this file**. Copy it from a template (`.env.example`, if present) and fill in real values. |
| `requirements.txt` | Pinned Python dependencies for the backend (FastAPI, LangGraph, LangChain, ChromaDB, sentence-transformers, etc.). |
| `run.py` | The simplest way to start the backend locally — a thin `uvicorn` launcher. |
| `serve_medgemma_colab.ipynb` | A ready-to-run Google Colab notebook that loads MedGemma via `transformers` on a free T4 GPU, wraps it in a small FastAPI server, and tunnels it out publicly (via ngrok) so the backend can reach it. This is the imaging model's actual serving mechanism — see the backend README's notes on `imaging/medgemma_client.py` for why this approach was chosen over vLLM. |

## Dependencies

Full pinned versions live in `requirements.txt`; the notable categories are:

- **Web framework:** `fastapi`, `uvicorn`, `python-multipart`
- **Data validation / config:** `pydantic`, `pydantic-settings`, `python-dotenv`
- **Database:** `sqlalchemy`
- **Agent orchestration:** `langgraph`, `langchain`, `langchain-core`
- **LLM providers:** `langchain-anthropic`, `langchain-openai`
- **RAG / retrieval:** `langchain-chroma`, `chromadb`, `langchain-huggingface`, `langchain-community` (for `BM25Retriever`), `sentence-transformers`, `rank-bm25`
- **Data access:** `huggingface_hub` (direct file-level dataset downloads for knowledge-base ingestion)
- **Web search:** `exa-py`
- **Voice:** `elevenlabs`
- **Imaging (Colab notebook, not the backend's own requirements.txt):** `transformers`, `accelerate`, `torch`, `fastapi`, `uvicorn`, `pyngrok`, `nest_asyncio`
- **Utilities:** `httpx`, `tenacity`, `loguru`

## Configuration

All configuration is centralized under `backend/config/` (see the backend
README for the full field-by-field breakdown) and loaded from a single
`.env` file via `pydantic-settings` + explicit `python-dotenv` loading.
Nothing in application code hardcodes a model name, API key, retrieval `k`,
or confidence threshold — every tunable value lives in one typed settings
object.

At minimum you'll need to set:
- An LLM provider key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
- `EXA_API_KEY` for web search
- `ELEVENLABS_API_KEY` for voice
- `MEDGEMMA_BASE_URL` pointing at wherever your MedGemma server is running (Colab tunnel URL, or your own GPU)

## Installation

```bash
# 1. Clone/unzip the project, then set up the backend environment
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env             # if provided — otherwise create .env directly
# edit .env and fill in your API keys

# 3. Seed the knowledge base (one-time; safe to re-run, skips work if already done)
python -m scripts.ingest_pubmed --limit 10000
```

## Running the Project

```bash
# Start the backend (from backend/, with the venv active)
python run.py
# API live at http://localhost:8000 — interactive docs at /docs

# In a separate terminal, serve the frontend (from frontend/)
python -m http.server 5500
# Open http://localhost:5500

# Serve MedGemma (open serve_medgemma_colab.ipynb in Google Colab)
# Run all cells, copy the printed tunnel URL into MEDGEMMA_BASE_URL in .env,
# restart the backend.
```

## Using the Application

- **Ask a clinical question** — type or speak it; the system routes it
  automatically to the knowledge base or a live web search as needed.
- **Upload a medical image** — attach it and describe what to analyze; the
  finding is queued for clinician review automatically.
- **Listen to any answer** — a play/pause/stop control on every response
  reads it aloud without re-fetching audio on every click.
- **Review flagged answers** — the sidebar's pending-review panel is where a
  clinician approves, edits, or rejects anything flagged for sign-off.
- **Revisit past consultations** — conversation history, including
  previously uploaded images, persists and reloads correctly when switching
  between conversations.

## API and Token References

| Service | Used for | Get a key |
|---|---|---|
| Anthropic | Main chat/reasoning LLM + guardrails | https://console.anthropic.com/settings/keys |
| OpenAI (alternative) | Same, if not using Anthropic | https://platform.openai.com/api-keys |
| Exa.ai | Real-time web search | https://dashboard.exa.ai/login |
| ElevenLabs | Speech-to-text and text-to-speech | https://elevenlabs.io → Profile → API Keys |
| HuggingFace | Downloading the embedding model; higher rate limits for MedGemma | https://huggingface.co/settings/tokens |

No key is required to be self-hosted for the imaging model — MedGemma runs
via the provided Colab notebook on a free GPU, tunneled to your backend.

## Logging

The backend uses `loguru`, writing to both the console and a rotating log
file under `data/`. Every guardrail decision, routing choice, retrieval
relevance verdict, and agent handoff is logged with enough detail to trace
exactly why a given answer took the path it did — useful both for debugging
and for auditing why a particular response was or wasn't flagged for review.

## Limitations

- **Not a diagnostic device.** Every disclaimer in this system is meant
  literally — this is decision *support*, not a replacement for clinical
  judgment.
- **Knowledge base is a fixed snapshot.** The PubMed corpus is ingested once,
  at a point in time — it doesn't update itself; the web search fallback
  exists specifically to cover what the snapshot can't.
- **Free-tier imaging hosting is ephemeral.** Running MedGemma via the
  Colab notebook is genuinely free but session-limited — fine for
  development/demos, not for depending on 24/7 uptime.
- **SQLite, not a production database.** Fine for development and modest
  usage; a real deployment serving many concurrent clinicians would want a
  managed database instead.
- **No authentication layer.** As shipped, there's no login/role system
  distinguishing clinicians from reviewers — anyone with access to the
  frontend can use every feature, including the review queue.
- **Guardrails are LLM-based, not infallible.** Both the input and output
  guardrails are model calls, not hard-coded rules — they materially reduce
  risk but shouldn't be treated as a perfect safety net on their own.
