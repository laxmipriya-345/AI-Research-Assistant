# AI Research Assistant

A full-stack research assistant with:

- **Chat with Documents** — upload PDF/DOCX/TXT files; the agent retrieves relevant passages via TF-IDF search (no embedding API needed).
- **Web Search Tool** — the agent can search the live web (DuckDuckGo, no API key required) when it needs current information.
- **Conversation Memory** — each session's chat history is stored in SQLite; older turns are auto-summarized so long sessions stay coherent without blowing up context.
- **Multi-step Reasoning** — the agent runs an iterative tool-use loop (web search → document search → save note → ...) before producing a final answer, up to a configurable step limit.
- **Research Notes** — save findings manually or let the agent save them for you via the `save_note` tool; notes persist per session.

## Stack

- Backend: Python, FastAPI, SQLite, Anthropic SDK
- Frontend: plain HTML/CSS/JS (no build step)

## Project Structure

```
ai-research-assistant/
├── backend/
│   ├── main.py          # FastAPI app & routes
│   ├── agent.py         # multi-step reasoning + tool-use loop
│   ├── memory.py        # conversation memory (SQLite)
│   ├── documents.py     # document ingestion + TF-IDF retrieval
│   ├── web_search.py    # web search tool
│   ├── notes.py         # research notes CRUD
│   ├── models.py        # Pydantic schemas
│   └── config.py        # settings
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/                 # created at runtime (SQLite DB + uploads)
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. **Install dependencies**

   ```bash
   cd ai-research-assistant
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure your API key**

   ```bash
   cp .env.example .env
   # edit .env and set ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **Run the server**

   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

4. **Open the app**

   Visit `http://localhost:8000` in your browser.

## How it works

1. Create a session in the sidebar.
2. Optionally upload documents (PDF/DOCX/TXT) — they're chunked and indexed for retrieval.
3. Ask a question in the chat box. Toggle "Web Search" / "Documents" on or off per message.
4. The agent (`backend/agent.py`) runs a loop: it may call `web_search`, `search_documents`, and/or `save_note` multiple times, reasoning over the results, before giving you a final answer. Each tool call is shown as a collapsed trail above the answer.
5. Notes appear in the right panel and persist across sessions (view/delete anytime).

## Notes & Extending

- Swap `documents.py`'s TF-IDF retrieval for a real embedding model/vector DB if you need semantic search at scale.
- `web_search.py` uses the `ddgs` package; swap in Bing/Google/Tavily/Serper if you have an API key and want more robust results.
- `MAX_REASONING_STEPS` and `MEMORY_SUMMARY_TRIGGER` in `.env` control how many tool-call rounds the agent gets and how aggressively memory gets summarized.
- The DB is a single SQLite file at `data/app.db` — fine for local/single-user use; swap for Postgres if you need multi-user concurrency.
