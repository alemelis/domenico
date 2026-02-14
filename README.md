# Domenico

Mobile-first AI build system: create projects, send instructions, see commits and diffs. One FastAPI app; projects live as separate git repos.

**Requires:** Python 3.13+, git

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8337
```

Open `http://<host>:8337/`.

## Config

| Variable | Default | Description |
|----------|---------|-------------|
| `DOMENICO_PROJECTS_ROOT` | `~/domenico-projects` | Root directory for project git repos |

SQLite DB: `data/db.sqlite3` (created on first run).

## Flow

1. **Home** — New Project (enter slug) → creates repo under `PROJECTS_ROOT/<slug>` with git, `README.md`, `memory.md`, and initial commit.
2. **Project page** — Open a project → command textarea + Run. Type an instruction, Run → agent applies changes, commits, returns last commit message and diff.
3. **MVP agent** — Dummy agent: writes a `dummy.txt` and appends to `memory.md`; no LLM yet. Real agent will use `agents/agent.md` and `skills/skills.md` to build prompts and return structured file updates.

## API (summary)

- `GET /` — Homepage (project list + New Project).
- `GET /projects` — JSON list of projects `{ id, slug, path, created_at }`.
- `POST /projects` — Body `{ "slug": "..." }`. Slug: `[a-zA-Z_][a-zA-Z0-9_-]*`. Returns `{ id, slug, path, message }`.
- `GET /projects/{id}` — Project view (command + output panel).
- `POST /projects/{id}/command` — Body `{ "instruction": "..." }`. Returns `{ commit_message, diff }`.

## Repo layout

- `app/main.py` — Routes and dummy agent.
- `app/templates/` — `index.html`, `project.html`.
- `core/db.py` — SQLite and `projects` table.
- `agents/agent.md`, `skills/skills.md` — For future LLM agent (role and skills text).
