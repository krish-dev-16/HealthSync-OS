# HealthSync OS

Autonomous clinical fulfillment engine, Cognizant BrAInstorm Challenge 2026 - MVP. 

Three CrewAI agents (Clinical Sentinel, PA Resolver, Supply Chain Orchestrator) run in sequence over synthetic patient data, then pause for a clinician to approve. All data is fictional.

1. **Clinical Sentinel:** A team of organ-specific agents (hepatic, renal, cardiac) simulates how a complex multi-drug regimen behaves over 72 hours. It catches cumulative toxicity and metabolic conflicts that pairwise checks miss, recommends dose adjustments, and writes an evidence-backed safety report.


2. **Prior Authorization Resolver:** This agent checks the patient’s history and the Sentinel’s report against the insurer’s clinical policy criteria. It then assembles the PA package and submits it through standard FHIR / X12 278 channels, so approval takes seconds instead of days.


3. **Predictive Supply Agent:** Once approval arrives, this agent checks pharmacy inventory. If stock is needed, it places a just-in-time EDI 850 purchase order timed to the patient’s appointment, which prevents both stockouts and expired-drug waste.

## Primary Techstack

- **Backend:** Python, FastAPI, CrewAI (`Process.sequential`), Gemini free tier
- **Frontend:** Vite + React, same layout and palette as the dashboard mockup
- **Data:** synthetic JSON written to `backend/data/` on first start. No database or cloud services.

## What is deterministic and what is the LLM

All numbers come from plain Python in `backend/tools.py`: the 72-hour PK curves, dose adjustment, policy criteria checks, FHIR `Claim`, inventory coverage and X12 EDI 850/855. The Gemini agents call those tools and write the clinical rationale, the justification letter and the supply summary.

If no `GEMINI_API_KEY` is set, or Gemini fails, the run falls back to template text for those three pieces so a demo never breaks. The header area shows which mode produced the current state.

## Setup (two terminals, from the project root)

Python 3.10 to 3.13 and Node 18+ are needed.

**Terminal 1: backend (Windows PowerShell)**

```
.venv\Scripts\activate
pip install -r backend\requirements.txt
cd backend
copy .env.example .env
notepad .env
uvicorn main:app --port 8000
```

On macOS or Linux use `source .venv/bin/activate` and `cp .env.example .env`.

In `.env`, paste a free key from https://aistudio.google.com/apikey. The model IDs `GEMINI_MODEL` and `GEMINI_FALLBACK_MODEL` are read from the same file. Check them against the model list in Google AI Studio and change them if Google has renamed a model.

**Terminal 2: frontend**

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to port 8000.

## Using the demo

1. The dashboard opens on `PT-1042` already loaded (Awaiting clinician approval).
2. **Review changes** shows the original vs. adjusted prescription, the matched policy citation and the queued EDI 850.
3. **Approve and submit** advances the prior authorization to Approved, dispatches the EDI 850 and confirms the 855.
4. Use the **Patient case** dropdown for the other two cases, **Reset case** to start a case over, and **Run CrewAI Pipeline** to run the live agents.
5. The Authorization, Supply Chain and Audit Trail tabs show the FHIR JSON, the raw X12 documents and the hash-chained log.

| Case | Shows |
| --- | --- |
| PT-1042 | Strong CYP3A4 inhibition, tacrolimus breaches the toxicity threshold, dose reduced, 40% stock |
| PT-2089 | No CYP interaction, 15% stock with 2 days of supply, step-therapy criterion checked |
| PT-3115 | Mild overlap, 85% stock, fast-track clearance |

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/patients` | Synthetic cases |
| `GET /api/workflow/{id}` | Current state |
| `POST /api/workflow/run/{id}` | Run the CrewAI pipeline |
| `POST /api/workflow/approve/{id}` | Clinician sign-off |
| `POST /api/workflow/reset/{id}` | Back to the pre-seeded state |
| `GET /api/health` | Whether a Gemini key is configured |

State is held in memory, so restarting the backend resets every case.

## Troubleshooting

- **"Something went wrong: Failed to fetch" in the page:** the backend is not running on port 8000.
- **Run takes a long time:** the free tier is limited to 8 requests per minute here (`max_rpm=8`), so three agents can take a minute or more.
- **Run says "used templates instead":** the note under the buttons lists the Gemini error for each model. Usually a wrong model ID or key.
- **Port 5173 or 8000 busy:** stop the other process, or change the port in `vite.config.js` and the `uvicorn` command.

Clinical figures, thresholds, policies and codes are synthetic and illustrative. This is not medical software.
