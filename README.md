# Briefboard

Paste your meeting notes, get a Kanban board.

Notes from meetings usually end up in a doc nobody opens again. Briefboard picks out the tasks, who should do them and by when, and puts them on a board you can drag around.

Live version: https://briefboard-xi.vercel.app

## What it does

- finds tasks, owners, deadlines and status in your notes (English and Polish)
- lays them out as Kanban, Scrum or Scrumban
- sorts cards by priority and gives them story points
- exports to Markdown, CSV or JSON

It works without any AI, it's just rules. Typos and very messy notes can confuse it.

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Then open http://localhost:8000. Tests: `pytest`.

## Using an LLM instead

Set these and it will use any OpenAI-compatible API (Groq, Ollama...). If the call fails it falls back to the rules.

```bash
export LLM_BASE_URL=https://api.groq.com/openai/v1
export LLM_API_KEY=your-key
export LLM_MODEL=llama-3.1-8b-instant
```

Built with Python, FastAPI and plain JavaScript.
