"""HealthSync OS API.

Run with:  uvicorn main:app --reload --port 8000
State lives in memory only (no database), so restarting the server resets the demo.
"""
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

import crew  # noqa: E402  (after load_dotenv so env vars are visible)
import tools as T  # noqa: E402
from seed_data import ensure_seed_data  # noqa: E402

STATE: dict = {}
LOCKS: dict = {}
STATE_GUARD = threading.Lock()


def _lock(patient_id: str) -> threading.Lock:
    with STATE_GUARD:
        return LOCKS.setdefault(patient_id, threading.Lock())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_seed_data()
    T.reload_data()
    # Pre-seed every case with the deterministic pipeline so the dashboard renders immediately.
    for p in T.get_patients():
        STATE[p["id"]] = crew.build_state(p["id"], mode="deterministic",
                                          llm_note="Pre-seeded state. Press Run CrewAI Pipeline to run the live agents.")
    yield


app = FastAPI(title="HealthSync OS API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require(patient_id: str) -> dict:
    if patient_id not in STATE:
        raise HTTPException(status_code=404, detail=f"Unknown patient {patient_id}")
    return STATE[patient_id]


@app.get("/api/health")
def health():
    import os
    return {"ok": True, "gemini_key_configured": bool(os.getenv("GEMINI_API_KEY", "").strip())}


@app.get("/api/patients")
def patients():
    return [
        {"id": p["id"], "label": p["label"], "scenario": p["scenario"], "name": p["name"],
         "age": p["age"], "sex": p["sex"], "diagnosis": p["diagnosis"]["text"]}
        for p in T.get_patients()
    ]


@app.get("/api/workflow/{patient_id}")
def get_workflow(patient_id: str):
    return _require(patient_id)


@app.post("/api/workflow/run/{patient_id}")
def run_workflow(patient_id: str):
    _require(patient_id)
    with _lock(patient_id):
        STATE[patient_id] = crew.run_pipeline(patient_id)  # blocking; FastAPI runs this in a worker thread
        return STATE[patient_id]


@app.post("/api/workflow/reset/{patient_id}")
def reset_workflow(patient_id: str):
    _require(patient_id)
    with _lock(patient_id):
        STATE[patient_id] = crew.build_state(patient_id, mode="deterministic", llm_note="Reset to the pre-seeded state.")
        return STATE[patient_id]


@app.post("/api/workflow/approve/{patient_id}")
def approve_workflow(patient_id: str):
    _require(patient_id)
    with _lock(patient_id):
        s = STATE[patient_id]
        if s["status"] == "approved":
            return s  # idempotent: a double click does not create a second claim or order

        now = datetime.now(timezone.utc)
        ts = now.isoformat(timespec="seconds")
        audit = s["audit_trail"]
        pa, sup = s["prior_auth"], s["supply"]

        crew.append_audit(audit, "Clinician", "clinician", "approved and submitted",
                          f"Approved the dose plan, prior authorization and purchase order for {patient_id}", "clinician sign-off (simulated)", ts)

        # Prior authorization: submitted -> payer review -> approved
        resp = T.build_claim_response(patient_id)
        pa["claim_response"] = resp
        pa["status"] = "Approved"
        pa["steps"] = [
            {"label": "Gathering evidence", "state": "done"},
            {"label": "Package compiled", "state": "done"},
            {"label": "Submitted with clinician approval", "state": "done"},
            {"label": "Payer review", "state": "done"},
            {"label": f"Approved ({resp['preAuthRef']})", "state": "done"},
        ]
        crew.append_audit(audit, "PA Resolver", "agent_step", "submitted FHIR Claim to payer",
                          f"Claim/{pa['claim']['id']} sent via simulated Da Vinci PAS endpoint", pa["document"], ts)
        crew.append_audit(audit, "System", "agent_step", "payer decision received",
                          f"ClaimResponse/{resp['id']}: {resp['disposition']}, {resp['preAuthRef']}", "simulated payer", ts)

        # Supply: 850 dispatched, 855 confirmed
        inv = T._load("specialty_inventory.json")["items"][patient_id]
        eta_h = inv["supplier"]["lead_time_hours"]
        sup["edi_850"]["status"] = "Dispatched"
        sup["edi_855"] = {"status": f"Confirmed (ETA {eta_h}h)", "raw": T.build_edi_855(patient_id, inv, sup["order_quantity"], now)}
        sup["rows"] = [
            {"label": "EDI 850 purchase order", "tone": "info", "text": "Dispatched"},
            {"label": "Supplier acknowledgment (855)", "tone": "ok", "text": f"Confirmed (ETA {eta_h}h)"},
        ]
        sup["eta"] = (now + timedelta(hours=eta_h)).isoformat(timespec="seconds")
        crew.append_audit(audit, "Supply Agent", "agent_step", "dispatched EDI 850",
                          f"{sup['order_quantity']} {sup['unit']}s to {sup['supplier']['name']}", "inventory_edi_tool", ts)
        crew.append_audit(audit, "Supply Agent", "agent_step", "received EDI 855 acknowledgment",
                          f"Confirmed, ETA {eta_h}h", sup["supplier"]["edi_id"], ts)

        s["stages"] = [
            {"label": "1 · Clinical Sentinel", "tone": "ok", "text": "Dose plan approved" if s["prescription"]["dose_adjusted"] else "Cleared"},
            {"label": "2 · PA Resolver", "tone": "ok", "text": "Approved"},
            {"label": "3 · Supply Agent", "tone": "ok", "text": "Dispatched"},
        ]
        s["header_badge"] = {"label": "Approved & Dispatched", "tone": "ok"}
        s["status"] = "approved"

        for who, action, detail, src in [
            ("Clinician", "approved the dose plan and submission", None, None),
            ("PA Resolver", "submitted FHIR Claim", f"Payer approved, {resp['preAuthRef']}", pa["document"]),
            ("Supply Agent", "dispatched EDI 850", f"Supplier confirmed (855), ETA {eta_h}h", sup["supplier"]["edi_id"]),
        ]:
            s["agent_trace"].append({"agent": who, "action": action, "detail": detail, "source": src, "timestamp": ts})
        # replace the "paused for approval" line's meaning: keep it, history is append-only
        return s
