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
