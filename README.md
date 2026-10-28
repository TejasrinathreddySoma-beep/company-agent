# Company Assistant

A local, privacy-friendly AI assistant that answers questions from your own documents, reads Gmail and Google Calendar through a custom MCP server, drafts emails, adds calendar events after you confirm them, and tracks its activity in PostgreSQL. The LLM runs locally with Ollama, so your documents never leave your machine.

## Features

- **Document Q&A (RAG):** ask questions about PDFs, text, Markdown and Word files. Answers come back in a clean structure (short definition, key points, limitations).
- **Grounded answers:** a similarity threshold returns "I couldn't find that" instead of guessing when no relevant passage exists.
- **Sources tab:** answers stay clean, and the supporting passages are in a collapsible *Sources* section.
- **Gmail:** list recent, unread or filtered emails as a readable table.
- **Email drafting:** "write a mail to ..." produces the email and saves it as a **Gmail draft**. The app never sends anything itself.
- **Google Calendar:** upcoming meetings plus holidays and festivals from all your calendars.
- **Add calendar events from chat:** "add team meeting tomorrow at 4 pm" shows a Confirm / Cancel card, and the event is created only after you click Confirm.
- **MCP server:** the Gmail and Calendar read tools are exposed through a custom Model Context Protocol server, and the agent connects to it as an MCP client.
- **PostgreSQL tracking:** questions, response times, calendar actions, email drafts and indexed documents are logged. The app keeps working if the database is down.
- **Offline-aware:** document questions work without internet. Gmail and Calendar questions return a friendly message when you are offline.
- **Streamlit UI:** chat interface with quick-question buttons, document upload with one-click re-indexing, an activity log, clear chat, and a per-question timing breakdown.

## How it works

```
Question
   |
   v
route()
   |-- documents -----> embed question -> FAISS search -> LLM writes formatted answer
   |-- email / calendar -> MCP client -> MCP server (server.py) -> Gmail / Calendar APIs
   |-- write a mail ----> LLM drafts email -> Gmail draft (not sent)
   |-- add an event ----> LLM extracts title/date/time -> Confirm card -> Calendar API
   |
   v
PostgreSQL activity log
```

1. `ingest.py` reads files from `docs/` and `notes/`, splits them into chunks (about 800 characters with 150 overlap), embeds them with `all-MiniLM-L6-v2`, stores them in a FAISS index, and records the files in PostgreSQL.
2. `agent.py` routes each question to the right path and logs the result.
3. `app.py` is the Streamlit front end, including the confirmation card for calendar events.

## Measured results

Measured from the project's own PostgreSQL activity log, running Llama 3.1 8B through Ollama on a laptop with an integrated GPU (Intel Core Ultra 5 125H).

| Metric | Result |
|---|---|
| Indexed corpus | 9 documents, 1,177 chunks |
| Document questions (5 queries) | median 16.7 s, mean 20.1 s end to end |
| Gmail and Calendar questions (2 queries) | about 15.4 s end to end |

This is a small sample (7 queries) and not a formal benchmark. The first query after startup includes model loading, which raises the mean. Most of the time is spent generating the answer with the local 8B model, while retrieval itself is a small fraction. The Timing panel in the app breaks each answer into retrieval, model load, prompt reading and generation speed (tokens per second).

## Project structure

```
agent/
├── agent.py            # routing, RAG, LLM calls, MCP client, email drafting, timing
├── app.py              # Streamlit chat UI
├── ingest.py           # builds the FAISS index from docs/ and notes/
├── server.py           # MCP server exposing the Gmail and Calendar read tools
├── tool.py             # Gmail and Calendar functions (Google API)
├── db.py               # PostgreSQL schema and logging helpers
├── requirements.txt
├── .env.example        # template for your local .env
├── docs/               # your documents (kept out of git)
├── notes/              # your private notes and Word files (kept out of git)
├── .gitignore
└── README.md
```

## Requirements

- Python 3.12+ (developed on 3.14, Windows)
- [Ollama](https://ollama.com) with a model pulled, for example `llama3.1:8b` (or the faster `llama3.2:3b`)
- PostgreSQL 16+ installed locally
- A Google account (for Gmail and Calendar)

## Setup

### 1. Create the virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Pull the local model

```powershell
ollama pull llama3.1:8b
```

If you use a different model, change `LLM = "..."` in `agent.py`.

### 3. Set up PostgreSQL

Install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/) (you can skip Stack Builder). Then open **SQL Shell (psql)**, log in as `postgres`, and run:

```sql
CREATE USER agent WITH PASSWORD 'choose-a-password';
CREATE DATABASE agent OWNER agent;
```

Copy `.env.example` to `.env` and fill it in:

```
DATABASE_URL=postgresql://agent:choose-a-password@localhost:5432/agent
```

Use a password with letters and numbers only, so the URL needs no encoding. The tables are created automatically the first time the app starts.

Check the connection:

```powershell
python -c "import db; print(db.init())"
```

It should print `True`.

### 4. Add your documents and build the index

Put files in `docs/` (and private notes in `notes/`), then:

```powershell
python ingest.py
```

Re-run this whenever the files change, or use the uploader in the app.

### 5. Set up Google access (Gmail and Calendar)

1. In the [Google Cloud Console](https://console.cloud.google.com), create a project and enable the **Gmail API** and **Google Calendar API**.
2. Configure the OAuth consent screen (External, Testing) and add your own Gmail address under **Test users**.
3. Create an **OAuth client ID** of type **Desktop app**, download the JSON and save it as `credentials.json` in the project folder.
4. Authorize once:

```powershell
python tool.py
```

A browser window opens, you approve access, and `token.json` is created. If you change the scopes in `tool.py` later, delete `token.json` and run this step again.

### 6. Run the app

```powershell
streamlit run app.py
```

Or use the terminal version (no confirm button for calendar events):

```powershell
python agent.py
```

## Example questions

| Question | Handled by |
|---|---|
| What is a vision transformer? | Documents (RAG) |
| Show my recent emails | Gmail tool |
| Any unread emails from SBI? | Gmail tool |
| Is there any holiday or festival this week? | Calendar tool |
| Write a mail to name@example.com wishing success in research | Email draft (saved to Gmail Drafts) |
| Add team meeting to my calendar tomorrow at 4 pm | Calendar event (asks you to confirm) |

## Database

| Table | Stores |
|---|---|
| `query_log` | question, route, response time and document sources. Answer text is stored only for document questions, never for Gmail or Calendar |
| `calendar_actions` | each proposed event and whether it was confirmed, cancelled or failed |
| `email_drafts` | recipient and subject of each draft created |
| `documents` | indexed files and their chunk counts |

Example query:

```sql
SELECT route, count(*), round(avg(seconds)::numeric, 1) AS avg_seconds
FROM query_log GROUP BY route;
```

## Configuration

Settings at the top of `agent.py`:

| Setting | Purpose |
|---|---|
| `LLM` | Ollama model name |
| `TOP_K` | Number of document chunks retrieved |
| `MIN_SCORE` | Minimum similarity for a chunk to be used (lower = more lenient) |

Environment variable in `.env`: `DATABASE_URL`.

## Performance notes

- The **Timing** expander in the UI shows retrieval time, model load, prompt reading and generation speed (tokens per second) for each question.
- LLM generation is the slowest step. A smaller model (for example `llama3.2:3b`) is usually the biggest speed-up.
- The embedding model is loaded from the local cache first, so startup does not depend on internet access.

## Limitations

- Single-user, local application: there is no login, and every user of the machine sees all indexed documents.
- Routing between documents, Gmail and Calendar uses keyword rules rather than a trained classifier.
- Answer quality and speed depend on the local 8B model and the laptop's integrated GPU.
- Relative dates such as "next Friday" are interpreted by the LLM, so the confirmation card shows the resolved date for you to check before anything is created.

## Security and privacy

- `credentials.json`, `token.json` and `.env` give access to your Google account and database. They are listed in `.gitignore`. **Never commit them.**
- Google permissions requested: read Gmail, create Gmail drafts, read Calendar, and create Calendar events. The app never sends email, and it creates a calendar event only after you click Confirm.
- Calendar creation is deliberately **not** exposed to the LLM as a tool, so the model cannot add events on its own.
- Emails and documents are treated as data. The assistant is instructed not to follow instructions found inside them.
- `docs/` and `notes/` contents are excluded from git so private files are not published.
- If a token leaks, delete `token.json` and revoke access at <https://myaccount.google.com/permissions>.

## Troubleshooting

| Problem | Fix |
|---|---|
| `could not open index.faiss` | run `python ingest.py` first |
| `credentials.json` not found | download it from Google Cloud and place it in the project folder |
| Google "access blocked" / 403 | add your Gmail address under OAuth consent screen, Test users |
| Calendar or draft creation fails with a permission error | delete `token.json` and run `python tool.py` again to grant the new scopes |
| `No module named 'mcp.server.fastmcp'` | MCP 2.x renamed it. Use `from mcp.server.mcpserver import MCPServer` |
| `No module named 'psycopg'` | `python -m pip install "psycopg[binary]"` |
| `[db] connection timeout` | wrong port in `DATABASE_URL`, or the PostgreSQL service is not running |
| `[db] password authentication failed` | the password in `.env` differs from the database user's. Reset it with `ALTER USER agent WITH PASSWORD '...';` |
| Pip installs into the wrong Python | use `python -m pip` with the venv activated |
| Slow answers | check `ollama ps`, try a smaller model, see the Timing panel |

## Tech stack

Python, Streamlit, Ollama, FAISS, sentence-transformers, Model Context Protocol (MCP), PostgreSQL (psycopg), Google Gmail and Calendar APIs, pypdf, python-docx.
