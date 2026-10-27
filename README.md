# Company Assistant

A local, privacy-friendly AI assistant that answers questions from your own documents and connects to Gmail and Google Calendar through an MCP server. The LLM runs locally with Ollama, so your documents never leave your machine.

## Features

- **Document Q&A (RAG):** ask questions about PDFs, text, Markdown and Word files. Answers are written in a clean, structured format (short definition, key points, limitations).
- **Sources tab:** answers stay clean, and the supporting passages are available in a collapsible *Sources* section.
- **Gmail:** list recent, unread or filtered emails as a readable table.
- **Google Calendar:** upcoming meetings, plus holidays and festivals from all your calendars.
- **MCP server:** Gmail and Calendar tools are exposed through a custom Model Context Protocol server, and the agent connects to it as an MCP client.
- **Offline-aware:** document questions work without internet. Gmail and Calendar questions return a friendly message when you are offline.
- **Streamlit UI:** chat interface with quick-question buttons, document upload with one-click re-indexing, clear chat, and a per-question timing breakdown.
- **Read-only access:** Google scopes are read-only, so the assistant cannot send, delete or change anything.

## How it works

```
Question
   |
   v
route() ──> documents ──> embed question ──> FAISS search ──> LLM writes formatted answer
   |
   └─────> email / calendar ──> MCP client ──> MCP server (server.py) ──> Gmail / Calendar APIs
```

1. `ingest.py` reads files from `docs/` and `notes/`, splits them into chunks, embeds them with `all-MiniLM-L6-v2`, and stores them in a FAISS index.
2. `agent.py` routes each question. Document questions retrieve the top chunks and a dedicated formatting prompt produces the answer. Email and calendar questions go through MCP tool calls.
3. `app.py` is the Streamlit front end.

## Project structure

```
agent/
├── agent.py            # routing, RAG, LLM calls, MCP client, timing
├── app.py              # Streamlit chat UI
├── ingest.py           # builds the FAISS index from docs/ and notes/
├── server.py           # MCP server exposing the Gmail and Calendar tools
├── tool.py             # Gmail and Calendar functions (Google API)
├── requirements.txt
├── docs/               # your documents (PDF, TXT, MD, DOCX)
├── notes/              # your private notes and Word files
├── .gitignore
└── README.md
```

## Requirements

- Python 3.12+ (developed on 3.14, Windows)
- [Ollama](https://ollama.com) with a model pulled, for example `llama3.1:8b` (or the faster `llama3.2:3b`)
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

### 3. Add your documents and build the index

Put files in `docs/` (and private notes in `notes/`), then:

```powershell
python ingest.py
```

Re-run this whenever the files change, or use the uploader in the app.

### 4. Set up Google access (Gmail and Calendar)

1. In the [Google Cloud Console](https://console.cloud.google.com), create a project and enable the **Gmail API** and **Google Calendar API**.
2. Configure the OAuth consent screen (External, Testing) and add your own Gmail address under **Test users**.
3. Create an **OAuth client ID** of type **Desktop app**, download the JSON and save it as `credentials.json` in the project folder.
4. Authorize once:

```powershell
python tool.py
```

A browser window opens, you approve read-only access, and `token.json` is created.

### 5. Run the app

```powershell
streamlit run app.py
```

Or use the terminal version:

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
| What meetings do I have next week? | Calendar tool |

## Configuration

Settings at the top of `agent.py`:

| Setting | Purpose |
|---|---|
| `LLM` | Ollama model name |
| `TOP_K` | Number of document chunks retrieved |
| `MIN_SCORE` | Minimum similarity for a chunk to be used (lower = more lenient) |

## Performance notes

- The **Timing** expander in the UI shows retrieval time, model load, prompt reading and generation speed (tokens per second) for each question.
- LLM generation is the slowest step. A smaller model (for example `llama3.2:3b`) is usually the biggest speed-up.
- The embedding model is loaded from the local cache first, so startup does not depend on internet access.

## Security

- `credentials.json`, `token.json` and `.env` give access to your Google account. They are listed in `.gitignore`. **Never commit them.**
- Google scopes are read-only.
- Emails and documents are treated as data. The assistant is instructed not to follow instructions found inside them.
- If a token leaks, delete `token.json` and revoke access at <https://myaccount.google.com/permissions>.

## Troubleshooting

| Problem | Fix |
|---|---|
| `could not open index.faiss` | run `python ingest.py` first |
| `credentials.json` not found | download it from Google Cloud and place it in the project folder |
| Google "access blocked" / 403 | add your Gmail address under OAuth consent screen, Test users |
| `No module named 'mcp.server.fastmcp'` | MCP 2.x renamed it. Use `from mcp.server.mcpserver import MCPServer` |
| Pip installs into the wrong Python | use `python -m pip` with the venv activated |
| Slow answers | check `ollama ps`, try a smaller model, see the Timing panel |

## Tech stack

Python, Streamlit, Ollama, FAISS, sentence-transformers, Model Context Protocol (MCP), Google Gmail and Calendar APIs, pypdf, python-docx.
