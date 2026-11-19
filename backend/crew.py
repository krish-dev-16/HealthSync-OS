"""CrewAI crew (3 agents, sequential) and the WorkflowState builder.

Division of labour:
  * tools.py computes every number, policy check and payload deterministically.
  * The agents call those tools and write the clinical rationale, the justification
    letter and the supply summary (Pydantic-validated task outputs).
  * build_state() merges both into one validated WorkflowState the frontend renders.

If no Gemini key is set, or the model calls fail, run_pipeline() falls back to
deterministic narrative text so a live demo never breaks. The state records which
mode produced it ("crewai_live" or "deterministic").
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

import tools as T

# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class SentinelReport(BaseModel):
    severity: str = Field(description="none, mild, moderate or severe")
    dose_recommendation: str = Field(description="One sentence with the proposed dose change, or that no change is needed")
    rationale: str = Field(description="2 to 4 sentences of clinical rationale citing the simulated peaks and the toxicity threshold")


class PAReport(BaseModel):
    status: str = Field(description="Draft ready, or Criteria gap")
    policy_citation: str = Field(description="The exact policy citation returned by the tool")
    summary: str = Field(description="2 to 3 sentences on which criteria were verified and the evidence")
    justification_letter: str = Field(description="A short clinical justification letter for the payer")


class SupplyReport(BaseModel):
    coverage_summary: str = Field(description="1 to 2 sentences on stock coverage versus the appointment")
    fulfillment_eta: str = Field(description="ETA for the queued purchase order")
    summary: str = Field(description="2 sentences on the queued EDI 850 order")


class Narrative(BaseModel):
    sentinel: SentinelReport
    pa: PAReport
    supply: SupplyReport


class TraceEntry(BaseModel):
    agent: str
    action: str
    detail: Optional[str] = None
    source: Optional[str] = None
    timestamp: str


class AuditEntry(BaseModel):
    seq: int
    timestamp: str
    actor: str
    kind: str  # agent_step | tool_call | citation | agent_output | clinician | system
    action: str
    detail: Optional[str] = None
    source: Optional[str] = None
    prev_hash: str
    hash: str


class WorkflowState(BaseModel):
    patient_id: str
    patient: Dict[str, Any]
    status: str  # awaiting_approval | approved
    mode: str  # crewai_live | deterministic
    model_used: Optional[str] = None
    llm_note: Optional[str] = None
    generated_at: str
    header_badge: Dict[str, str]
    stages: List[Dict[str, str]]
    interaction: Dict[str, Any]
    simulation: Dict[str, Any]
    prescription: Dict[str, Any]
    prior_auth: Dict[str, Any]
    supply: Dict[str, Any]
    agent_trace: List[TraceEntry]
    audit_trail: List[AuditEntry]


# --------------------------------------------------------------------------- #
# Audit chain (append-only, each entry hashes the one before it)
# --------------------------------------------------------------------------- #


def append_audit(audit: list, actor: str, kind: str, action: str, detail: str = None, source: str = None, ts: str = None) -> dict:
    prev = audit[-1]["hash"] if audit else "GENESIS"
    entry = {
        "seq": len(audit) + 1,
        "timestamp": ts or T.now_iso(),
        "actor": actor,
        "kind": kind,
        "action": action,
        "detail": detail,
        "source": source,
        "prev_hash": prev,
    }
    digest = hashlib.sha256((prev + json.dumps(entry, sort_keys=True)).encode()).hexdigest()
    entry["hash"] = digest[:16]
    audit.append(entry)
    return entry


# --------------------------------------------------------------------------- #
# Deterministic narrative (used when the LLM is unavailable)
# --------------------------------------------------------------------------- #


def deterministic_narrative(sim: dict, pa: dict, sup: dict) -> Narrative:
    u = sim["unit"]
    if sim["dose_adjusted"]:
        rec = (f"Reduce {sim['victim_drug']} from {sim['original_dose_mg']} mg to {sim['adjusted_dose_mg']} mg every {sim['interval_h']} h "
               f"while the interacting regimen is active.")
        why = (f"{sim['perpetrator']} inhibits {sim['enzyme']}, cutting clearance of {sim['victim_drug']} by about {sim['clearance_reduction_factor']}x. "
               f"At the original dose the simulated 72-hour peak reaches {sim['peak_original']} {u}, above the {sim['toxicity_threshold']} {u} toxicity threshold. "
               f"At the adjusted dose the peak is {sim['peak_adjusted']} {u}, inside the safe range.")
    else:
        rec = "No dose change needed."
        why = (f"The simulated 72-hour peak for {sim['victim_drug']} is {sim['peak_original']} {u}, well under the {sim['toxicity_threshold']} {u} toxicity threshold. "
               f"Interaction severity is {sim['interaction_severity']}.")
    met = sum(1 for c in pa["criteria"] if c["met"])
    pa_sum = f"{met} of {len(pa['criteria'])} policy criteria were verified against the chart. {pa['citation']}."
    letter = pa["justification_letter"]
    cov = (f"Stock covers {sup['coverage_pct']}% of the required quantity ({sup['stock_units']} of {sup['required_units']} {sup['unit']}s, "
           f"{sup['stock_days']} days of supply) with the appointment in {sup['days_until_appointment']} days.")
    eta = sup["eta"][:10]
    return Narrative(
        sentinel=SentinelReport(severity=sim["interaction_severity"], dose_recommendation=rec, rationale=why),
        pa=PAReport(status="Draft ready" if pa["all_criteria_met"] else "Criteria gap", policy_citation=pa["citation"], summary=pa_sum, justification_letter=letter),
        supply=SupplyReport(coverage_summary=cov, fulfillment_eta=eta,
                            summary=f"Queued an EDI 850 purchase order for {sup['order_quantity']} {sup['unit']}s. Estimated delivery {eta}."),
    )


# --------------------------------------------------------------------------- #
# State builder
# --------------------------------------------------------------------------- #


def build_state(patient_id: str, narrative: Optional[Narrative] = None, mode: str = "deterministic",
                model_used: Optional[str] = None, llm_note: Optional[str] = None) -> dict:
    patient = T.get_patient(patient_id)
    sim = T.pk_pd_simulation(patient_id)
    pa = T.payer_policy_lookup(patient_id, interaction_review_complete=True)
    sup = T.inventory_edi(patient_id)
    narrative = narrative or deterministic_narrative(sim, pa, sup)
    n_med = len(patient["medications"])
    ts0 = T.now_iso()

    u = sim["unit"]
    drug = sim["victim_drug"]
    if sim["threshold_breached_original"]:
        s1 = (f"Threshold exceeded for {drug}", f"Original dose peaks at {sim['peak_original']} {u} (threshold {sim['toxicity_threshold']} {u})")
        s2 = ("proposed dose adjustment", f"Re-simulated at {sim['adjusted_dose_mg']} mg, peak {sim['peak_adjusted']} {u}, within safe range")
    else:
        s1 = (f"Below toxicity threshold for {drug}", f"{drug} peaks at {sim['peak_original']} {u}, below the {sim['toxicity_threshold']} {u} threshold")
        s2 = ("checked dose plan", "No dose adjustment needed")

    trace = [
        TraceEntry(agent="Sentinel", action="ran 72-hour simulation", detail=s1[0], source="pk_pd_simulation_tool", timestamp=ts0),
        TraceEntry(agent="Sentinel", action=s2[0], detail=s2[1], source="pk_pd_simulation_tool", timestamp=ts0),
        TraceEntry(agent="PA Resolver", action="matched payer policy", detail=pa["citation"], source=pa["document"], timestamp=ts0),
        TraceEntry(agent="PA Resolver", action="verified clinical criteria",
                   detail=f"{sum(c['met'] for c in pa['criteria'])} of {len(pa['criteria'])} met, FHIR Claim compiled", source="payer_policy_lookup_tool", timestamp=ts0),
        TraceEntry(agent="Supply Agent", action="checked specialty inventory",
                   detail=f"Coverage {sup['coverage_pct']}% ({sup['stock_units']} of {sup['required_units']} {sup['unit']}s)", source="inventory_edi_tool", timestamp=ts0),
        TraceEntry(agent="Supply Agent", action="queued EDI 850 purchase order",
                   detail=f"{sup['order_quantity']} {sup['unit']}s, ETA {sup['eta'][:10]}", source="inventory_edi_tool", timestamp=ts0),
        TraceEntry(agent="System", action="paused for clinician approval", detail=None, source=None, timestamp=ts0),
    ]

    audit: list = []
    append_audit(audit, "System", "system", "workflow started", f"{patient_id}, mode {mode}", ts=ts0)
    append_audit(audit, "Sentinel", "tool_call", "pk_pd_simulation_tool",
                 f"{perp(sim)} vs {drug}: clearance /{sim['clearance_reduction_factor']}, peaks base {sim['peak_baseline']}, original {sim['peak_original']}, adjusted {sim['peak_adjusted']} {u}",
                 "pk_pd_simulation_tool", ts0)
    append_audit(audit, "Sentinel", "agent_output", "interaction report", f"{narrative.sentinel.dose_recommendation} {narrative.sentinel.rationale}", None, ts0)
    append_audit(audit, "PA Resolver", "tool_call", "payer_policy_lookup_tool",
                 "; ".join(f"{c['id']}: {'met' if c['met'] else 'NOT MET'} ({c['evidence']})" for c in pa["criteria"]), "payer_policies.json", ts0)
    append_audit(audit, "PA Resolver", "citation", "policy section cited", pa["citation"], pa["document"], ts0)
    append_audit(audit, "PA Resolver", "agent_output", "prior authorization package", narrative.pa.summary, None, ts0)
    append_audit(audit, "Supply Agent", "tool_call", "inventory_edi_tool",
                 f"coverage {sup['coverage_pct']}%, stock {sup['stock_days']} days, appointment in {sup['days_until_appointment']} days, order {sup['order_quantity']} {sup['unit']}s",
                 "specialty_inventory.json", ts0)
    append_audit(audit, "Supply Agent", "agent_output", "fulfillment plan", f"{narrative.supply.coverage_summary} {narrative.supply.summary}", None, ts0)
    append_audit(audit, "System", "system", "paused for clinician approval", "No claim or purchase order is sent until a clinician approves", None, ts0)

    stages = [
        {"label": "1 · Clinical Sentinel", "tone": "warn" if sim["dose_adjusted"] else "ok",
         "text": "Warning · dose adjusted" if sim["dose_adjusted"] else "Cleared · no dose change"},
        {"label": "2 · PA Resolver", "tone": "info" if pa["all_criteria_met"] else "warn",
         "text": narrative.pa.status},
        {"label": "3 · Supply Agent", "tone": "idle", "text": "Queued"},
    ]

    state = {
        "patient_id": patient_id,
        "patient": {
            "id": patient["id"], "label": patient["label"], "scenario": patient["scenario"], "name": patient["name"],
            "age": patient["age"], "sex": patient["sex"], "diagnosis": patient["diagnosis"],
            "medication_count": n_med, "medications": patient["medications"], "new_rx": patient["new_rx"],
            "payer": pa["payer"], "days_until_appointment": patient["days_until_appointment"],
        },
        "status": "awaiting_approval",
        "mode": mode,
        "model_used": model_used,
        "llm_note": llm_note,
        "generated_at": ts0,
        "header_badge": {"label": "Awaiting clinician approval", "tone": "warn"},
        "stages": stages,
        "interaction": {
            "graph": sim["interaction_graph"], "severity": sim["interaction_severity"], "enzyme": sim["enzyme"],
            "saturation": sim["enzyme_saturation"], "perpetrator": sim["perpetrator"],
            "subtitle": (f"New prescription competes for the {sim['enzyme']} pathway" if sim["enzyme"] else "New prescription does not use a cytochrome P450 pathway"),
        },
        "simulation": {k: sim[k] for k in [
            "hours", "baseline", "original", "adjusted", "unit", "toxicity_threshold", "therapeutic_window", "peak_original",
            "peak_adjusted", "peak_baseline", "threshold_breached_original", "threshold_breached_adjusted", "victim_drug"]},
        "prescription": {
            "drug": sim["victim_drug"],
            "original": {"dose_mg": sim["original_dose_mg"], "interval_h": sim["interval_h"]},
            "adjusted": {"dose_mg": sim["adjusted_dose_mg"], "interval_h": sim["interval_h"], "multiplier": sim["dose_multiplier"]},
            "dose_adjusted": sim["dose_adjusted"],
            "recommendation": narrative.sentinel.dose_recommendation,
            "rationale": narrative.sentinel.rationale,
            "new_rx": patient["new_rx"],
        },
        "prior_auth": {
            "status": narrative.pa.status,
            "steps": [
                {"label": "Gathering evidence", "state": "done"},
                {"label": "Package compiled", "state": "done"},
                {"label": "Awaiting approval to submit", "state": "current"},
                {"label": "Payer review", "state": "todo"},
                {"label": "Approved", "state": "todo"},
            ],
            "payer": pa["payer"], "policy_id": pa["policy_id"], "policy_title": pa["policy_title"], "document": pa["document"],
            "section": pa["section"], "section_title": pa["section_title"], "citation": narrative.pa.policy_citation or pa["citation"],
            "codes": pa["codes"], "criteria": pa["criteria"], "all_criteria_met": pa["all_criteria_met"],
            "summary": narrative.pa.summary, "claim": pa["claim"], "claim_response": None,
            "justification_letter": narrative.pa.justification_letter or pa["justification_letter"],
        },
        "supply": {
            "ndc": sup["ndc"], "product": sup["product"], "unit": sup["unit"], "stock_units": sup["stock_units"],
            "required_units": sup["required_units"], "stock_days": sup["stock_days"],
            "days_until_appointment": sup["days_until_appointment"], "appointment_date": sup["appointment_date"],
            "reorder_threshold_units": sup["reorder_threshold_units"], "below_reorder_threshold": sup["below_reorder_threshold"],
            "coverage_pct": sup["coverage_pct"], "stockout_risk": sup["stockout_risk"], "supplier": sup["supplier"],
            "order_quantity": sup["order_quantity"], "order_total_usd": sup["order_total_usd"], "eta": sup["eta"],
            "eta_before_appointment": sup["eta_before_appointment"], "coverage_summary": narrative.supply.coverage_summary,
            "summary": narrative.supply.summary, "fulfillment_eta": narrative.supply.fulfillment_eta,
            "edi_850": sup["edi_850"], "edi_855": sup["edi_855"],
            "rows": [
                {"label": "EDI 850 purchase order", "tone": "idle", "text": "Queued"},
                {"label": "Supplier acknowledgment (855)", "tone": "idle", "text": "Pending"},
            ],
        },
        "agent_trace": [t.model_dump() for t in trace],
        "audit_trail": audit,
    }
    return WorkflowState(**state).model_dump()


def perp(sim: dict) -> str:
    return sim["perpetrator"]


# --------------------------------------------------------------------------- #
# Live CrewAI run
# --------------------------------------------------------------------------- #


def _make_llm(model: str):
    from crewai import LLM
    return LLM(model=model, api_key=os.getenv("GEMINI_API_KEY"), temperature=0.2)


def _run_crew(patient_id: str, model: str) -> Narrative:
    from crewai import Agent, Crew, Process, Task

    patient = T.get_patient(patient_id)
    llm = _make_llm(model)
    brief = (f"Synthetic patient {patient_id}: {patient['age']}{patient['sex']}, {patient['diagnosis']['text']}. "
             f"New prescription: {patient['new_rx']['name']} ({patient['new_rx']['regimen']}). "
             f"{len(patient['medications'])} active medications. Appointment in {patient['days_until_appointment']} days. All data is synthetic.")

    sentinel = Agent(
        role="Clinical Sentinel",
        goal="Screen the new prescription for multi-drug toxicity and propose a safe dose.",
        backstory="A clinical pharmacology agent that relies only on the pk_pd_simulation_tool for numbers.",
        tools=[T.pk_pd_simulation_tool], llm=llm, max_rpm=8, allow_delegation=False, verbose=False, max_iter=4,
    )
    resolver = Agent(
        role="PA Resolver",
        goal="Verify payer policy criteria and prepare the prior authorization package.",
        backstory="A prior authorization specialist that cites the exact policy section the tool returns.",
        tools=[T.payer_policy_lookup_tool], llm=llm, max_rpm=8, allow_delegation=False, verbose=False, max_iter=4,
    )
    supply = Agent(
        role="Supply Chain Orchestrator",
        goal="Make sure specialty stock covers the appointment and queue a purchase order if it does not.",
        backstory="A supply chain agent that relies only on the inventory_edi_tool for stock and order figures.",
        tools=[T.inventory_edi_tool], llm=llm, max_rpm=8, allow_delegation=False, verbose=False, max_iter=4,
    )

    t1 = Task(
        description=f"{brief}\nCall pk_pd_simulation_tool with patient_id \"{patient_id}\". Report the interaction severity, the proposed dose change and a short rationale using only the tool's numbers.",
        expected_output="A SentinelReport.", agent=sentinel, output_pydantic=SentinelReport,
    )
    t2 = Task(
        description=f"{brief}\nCall payer_policy_lookup_tool with patient_id \"{patient_id}\". Report whether each criterion was met, quote the citation exactly as returned, and write a short justification letter that mentions the Clinical Sentinel's dose plan.",
        expected_output="A PAReport.", agent=resolver, output_pydantic=PAReport, context=[t1],
    )
    t3 = Task(
        description=f"{brief}\nCall inventory_edi_tool with patient_id \"{patient_id}\". Report stock coverage versus the appointment, and the ETA of the queued EDI 850 order.",
        expected_output="A SupplyReport.", agent=supply, output_pydantic=SupplyReport, context=[t2],
    )
    crew = Crew(agents=[sentinel, resolver, supply], tasks=[t1, t2, t3], process=Process.sequential, max_rpm=8, verbose=False)
    crew.kickoff()
    outs = [t.output.pydantic if t.output else None for t in (t1, t2, t3)]
    if any(o is None for o in outs):
        raise RuntimeError("Crew finished without structured output for every agent")
    return Narrative(sentinel=outs[0], pa=outs[1], supply=outs[2])


def run_pipeline(patient_id: str) -> dict:
    """Run the live crew if a key is configured, otherwise (or on failure) the deterministic path."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    primary = os.getenv("GEMINI_MODEL", "gemini/gemini-4-hydrogen")
    fallback = os.getenv("GEMINI_FALLBACK_MODEL", "gemini/gemini-3.5-flash-lite")
    if not key:
        return build_state(patient_id, mode="deterministic", llm_note="GEMINI_API_KEY is not set, so agent text was generated from templates.")
    errors = []
    for model in dict.fromkeys([primary, fallback]):
        try:
            narrative = _run_crew(patient_id, model)
            return build_state(patient_id, narrative, mode="crewai_live", model_used=model)
        except Exception as exc:  # noqa: BLE001 - any LLM/network/schema failure should fall through
            errors.append(f"{model}: {type(exc).__name__}: {str(exc)[:160]}")
    return build_state(patient_id, mode="deterministic", llm_note="Gemini calls failed, used templates instead. " + " | ".join(errors))
