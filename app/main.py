import os
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import subprocess

from core import db
from datetime import datetime

db.init_db()

# Configurable projects root
PROJECTS_ROOT = Path(os.getenv("DOMENICO_PROJECTS_ROOT", "~/domenico-projects")).expanduser()
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI()

from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    slug: str


class CommandInput(BaseModel):
    instruction: str


class FileUpdate(BaseModel):
    path: str
    content: str


class AgentOutput(BaseModel):
    commit_message: str
    files: list[FileUpdate]
    memory_update: str


def dummy_agent(instruction: str) -> AgentOutput:
    """MVP dummy agent: create one file and fixed commit/memory. No LLM."""
    from datetime import datetime
    ts = datetime.utcnow().isoformat()
    return AgentOutput(
        commit_message="Dummy: apply instruction",
        files=[
            FileUpdate(path="dummy.txt", content=f"Instruction: {instruction}\nRecorded: {ts}\n")
        ],
        memory_update=f"\n## {ts}\nInstruction: {instruction}\nOutcome: Dummy file created.\n",
    )


def apply_agent_output(project_path: Path, output: AgentOutput) -> None:
    for f in output.files:
        fp = project_path / f.path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(f.content, encoding="utf-8")
    memory_path = project_path / "memory.md"
    memory_path.open("a", encoding="utf-8").write(output.memory_update)

@app.post("/projects")
def create_project(project: ProjectCreate):
    slug = project.slug
    # validate slug
    import re

    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_-]*", slug):
        raise HTTPException(status_code=400, detail="Invalid slug")

    project_path = PROJECTS_ROOT / slug
    if project_path.exists():
        raise HTTPException(status_code=400, detail="Project already exists")

    try:
        # Create directory
        project_path.mkdir(parents=True)
        # Initialize git
        subprocess.run(["git", "init"], cwd=project_path, check=True)
        # Create initial files
        (project_path / "README.md").write_text(f"# {slug}\n")
        (project_path / "memory.md").write_text("# Memory\n")
        # Initial commit
        subprocess.run(["git", "add", "."], cwd=project_path, check=True)
        subprocess.run(["git", "commit", "-m", "Initial bootstrap"], cwd=project_path, check=True)

        project_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        conn = db.get_connection()
        conn.execute("INSERT INTO projects (id, slug, path, created_at) VALUES (?, ?, ?, ?)",(project_id, slug, str(project_path), created_at))
        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse({
        "id": project_id,
        "slug": slug,
        "path": str(project_path),
        "message": "Project created successfully"
    })


def get_project_by_id(project_id: str):
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


@app.get("/projects")
def list_projects():
    conn = db.get_connection()
    rows = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_view(request: Request, project_id: str):
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return templates.TemplateResponse("project.html", {"request": request, "project": project})


@app.post("/projects/{project_id}/command")
def run_command(project_id: str, body: CommandInput):
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project_path = Path(project["path"])
    if not project_path.is_dir():
        raise HTTPException(status_code=500, detail="Project path not found")

    output = dummy_agent(body.instruction)
    apply_agent_output(project_path, output)

    try:
        subprocess.run(["git", "add", "."], cwd=project_path, check=True)
        subprocess.run(["git", "commit", "-m", output.commit_message], cwd=project_path, check=True)
        result = subprocess.run(
            ["git", "show", "--no-color", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        diff = result.stdout if result.returncode == 0 else ""
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Git error: {e}")

    return JSONResponse({"commit_message": output.commit_message, "diff": diff})