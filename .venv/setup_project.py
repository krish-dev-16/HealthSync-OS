"""
HealthSync OS project scaffolder.

Run from the project root (the folder that contains .venv):

    python setup_project.py

Safe to re-run: existing files are never overwritten.
The frontend is not created here; use the create-next-app command printed at the end.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Python packages (each gets an __init__.py)
PACKAGES = [
    "backend/app",
    "backend/app/api",
    "backend/app/agents",
    "backend/app/tools",
    "backend/app/rag",
    "backend/app/db",
    "backend/app/mock_payer",
    "backend/app/schemas",
    "backend/app/audit",
    "backend/tests",
]

# Plain folders (get a .gitkeep so Git tracks them while empty)
FOLDERS = [
    "backend/app/agents/prompts",
    "data/raw/payer_policies",
    "data/raw/clinical_notes",
    "data/raw/inventory",
    "data/markdown",
    "data/synthetic",
    "data/reference",
    "evaluation/results",
    "scripts",
    "docs",
]

# Empty placeholder modules, so the structure is visible in PyCharm immediately
MODULES = [
    "backend/app/main.py",
    "backend/app/config.py",
    "backend/app/api/workflow.py",
    "backend/app/api/stream.py",
    "backend/app/api/approvals.py",
    "backend/app/api/inventory.py",
    "backend/app/agents/state.py",
    "backend/app/agents/graph.py",
    "backend/app/agents/clinical_sentinel.py",
    "backend/app/agents/pa_resolver.py",
    "backend/app/agents/supply_agent.py",
    "backend/app/tools/pk_engine.py",
    "backend/app/tools/cyp_interactions.py",
    "backend/app/tools/renal.py",
    "backend/app/tools/fhir_builder.py",
    "backend/app/tools/edi.py",
    "backend/app/tools/inventory_tools.py",
    "backend/app/tools/rag_search.py",
    "backend/app/rag/ingest.py",
    "backend/app/rag/retriever.py",
    "backend/app/rag/embeddings.py",
    "backend/app/db/database.py",
    "backend/app/db/models.py",
    "backend/app/db/seed.py",
    "backend/app/mock_payer/router.py",
    "backend/app/audit/logger.py",
    "backend/tests/test_pk_engine.py",
    "backend/tests/test_fhir_builder.py",
    "backend/tests/test_graph.py",
    "evaluation/baseline_pairwise.py",
    "evaluation/run_eval.py",
    "scripts/run_ingest.py",
    "scripts/seed_demo_data.py",
    "docs/architecture.md",
    "docs/demo_script.md",
]

GITIGNORE = """\
# Environments
.venv/
.env

# Python
__pycache__/
*.pyc
.pytest_cache/
.ipynb_checkpoints/

# Local data stores and generated output
data/chroma_db/
data/markdown/
data/*.db
*.sqlite
*.db

# Frontend
frontend/node_modules/
frontend/.next/

# IDE / OS
.idea/
.vscode/
.DS_Store
Thumbs.db
"""

REQUIREMENTS = """\
# Versions intentionally unpinned; run `pip freeze > requirements.lock` once everything works.

# API
fastapi
uvicorn[standard]
sse-starlette
httpx
pydantic
pydantic-settings
python-dotenv

# Agents and local LLM
langgraph
langgraph-checkpoint-sqlite
langchain
langchain-ollama

# RAG
chromadb
langchain-chroma
langchain-text-splitters
markitdown[pdf,docx,xlsx]

# Domain logic
numpy
scipy
fhir.resources
sqlalchemy

# Testing
pytest
"""

ENV_EXAMPLE = """\
# Copy to .env and adjust
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=nomic-embed-text

CHROMA_DIR=./data/chroma_db
SQLITE_PATH=./data/healthsync.db
RAW_DIR=./data/raw
MARKDOWN_DIR=./data/markdown

# Mock payer runs inside the same FastAPI app
PAYER_BASE_URL=http://localhost:8000/mock-payer
"""

README = """\
# HealthSync OS: Autonomous Clinical Fulfillment Engine

Local, privacy-first multi-agent system: clinical safety validation,
prior authorization, and just-in-time supply fulfillment.

## Quick start

1. `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text`
2. `pip install -r requirements.txt` (inside the .venv)
3. Copy `.env.example` to `.env`
4. Ingest documents: `python scripts/run_ingest.py`
5. Run the API: `uvicorn backend.app.main:app --reload`
6. Frontend: `cd frontend` then `npm run dev`
"""


def write_if_missing(path: Path, content: str = "") -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    created = 0

    for pkg in PACKAGES:
        (ROOT / pkg).mkdir(parents=True, exist_ok=True)
        created += write_if_missing(ROOT / pkg / "__init__.py")

    for folder in FOLDERS:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
        created += write_if_missing(ROOT / folder / ".gitkeep")

    for module in MODULES:
        created += write_if_missing(ROOT / module)

    created += write_if_missing(ROOT / ".gitignore", GITIGNORE)
    created += write_if_missing(ROOT / "requirements.txt", REQUIREMENTS)
    created += write_if_missing(ROOT / ".env.example", ENV_EXAMPLE)
    created += write_if_missing(ROOT / "README.md", README)
    created += write_if_missing(ROOT / "evaluation" / "test_cases.json", "[]\n")

    print(f"Done. Created {created} new files (existing files were left untouched).")
    print("\nNext steps:")
    print("  1. pip install -r requirements.txt")
    print("  2. Create the frontend:  npx create-next-app@latest frontend")
    print("  3. In PyCharm: right-click the 'backend' folder > Mark Directory as > Sources Root")


if __name__ == "__main__":
    main()