# Briefboard

Turn raw meeting notes into a prioritised delivery board. Paste minutes, bullet points or a transcript and get a Kanban, Scrum or Scrumban board with owners, due dates, priorities, story points and a coaching summary.

Built with FastAPI and vanilla JavaScript. Runs entirely free: the default engine is a rule-based parser that works offline, and an LLM can be plugged in optionally.

## Features

- **Notes to board** - detects action items, owners (`Anna:`, `Piotr will ...`, `@marek`, `owner: Zofia`), due dates (`by Friday`, `2026-11-12`, `5.11`, `tomorrow`, `next week`), `#labels`, explicit estimates (`8 pts`) and status (`done`, `in review`, `in progress`, `blocked`)
- **English and Polish** notes out of the box
- **Agile methods** - Kanban with WIP limits, Scrum with sprint planning against velocity, Scrumban with a Ready buffer; switch live without regenerating
- **WSJF scoring** and **MoSCoW** classification for every card, Fibonacci story points, bug and spike heuristics
- **Coach notes** - WIP breaches, overdue and blocked work, unassigned cards, oversized stories, workload imbalance, sprint over-commitment
- **Decisions, risks and open questions** extracted into their own panel
- Drag and drop board, card editor, local persistence
- Export to Markdown, CSV and JSON, print-friendly layout
- Built-in agile playbook (Definition of Ready and Done, WSJF, MoSCoW, story points)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000 and load one of the samples.

## Tests

```bash
pytest
```

## Optional LLM extraction

By default notes are parsed by the rule engine and never leave your machine. To let an LLM structure the notes instead, point Briefboard at any OpenAI-compatible endpoint. If the call fails the rule engine takes over.

```bash
export LLM_BASE_URL=https://api.groq.com/openai/v1
export LLM_API_KEY=your-key
export LLM_MODEL=llama-3.1-8b-instant
```

For a fully local setup use Ollama:

```bash
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=llama3.1
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/analyze` | Notes to board and metrics |
| POST | `/api/refresh` | Re-score cards and recompute metrics |
| POST | `/api/method` | Switch between Kanban, Scrum and Scrumban |
| POST | `/api/export` | Download as `csv`, `markdown` or `json` |
| GET | `/api/playbook` | Agile reference content |
| GET | `/api/sample` | Sample notes (`?lang=en` or `pl`) |

## Project layout

```
app/        FastAPI app, parser, scoring and agile logic
public/     Static frontend
api/        Vercel entrypoint
tests/      Pytest suite
```

## Scoring

```
WSJF = (value + urgency + bug uplift) / story points
```

Value comes from priority (critical 13, high 8, medium 5, low 2), urgency from the due date, and a bug adds 3. Critical cards are Must, high cards with a deadline are Must, postponed cards are Won't. Scrum planning always commits Must-have cards and fills the rest by score until velocity is reached.

## License

MIT
