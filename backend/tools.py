"""Deterministic tools for the three HealthSync OS agents.

All clinical math, policy checks, FHIR payloads and X12 documents are produced here
in plain Python, so the numbers on the dashboard never depend on the LLM. The agents
call the `@tool` wrappers at the bottom; the workflow builder in crew.py calls the
pure functions directly.
"""
import json
import math
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

try:  # CrewAI is only needed for the agent wrappers
    from crewai.tools import tool
except Exception:  # pragma: no cover - lets the pure functions be used without crewai
    def tool(_name):
        def deco(fn):
            return fn
        return deco

DATA_DIR = Path(__file__).parent / "data"
HOURS = list(range(0, 73, 6))  # 0h to 72h in 6-hour increments

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@lru_cache(maxsize=None)
def _load(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def reload_data():
    _load.cache_clear()


def get_patients():
    return _load("patients.json")


def get_patient(patient_id: str) -> dict:
    for p in get_patients():
        if p["id"] == patient_id:
            return p
    raise KeyError(f"Unknown patient {patient_id}")


# --------------------------------------------------------------------------- #
# 1. Clinical Sentinel: pharmacokinetic simulation
# --------------------------------------------------------------------------- #
def _conc(t: float, dose_mg: float, v: dict, ke: float) -> float:
    """One-compartment oral model with first-order absorption and repeat dosing (ng/mL)."""
    ka, f, vol_ml = v["ka_per_h"], v["bioavailability"], v["volume_L"] * 1000.0
    total = 0.0
    k = 0
    while k * v["interval_h"] <= t:
        dt = t - k * v["interval_h"]
        if abs(ka - ke) < 1e-9:
            ka_eff = ka + 1e-6
        else:
            ka_eff = ka
        total += (f * dose_mg * 1e6 * ka_eff / (vol_ml * (ka_eff - ke))) * (math.exp(-ke * dt) - math.exp(-ka_eff * dt))
        k += 1
    return total


def _curve(dose_mg: float, v: dict, ke: float):
    points = [round(_conc(h, dose_mg, v, ke), 2) for h in HOURS]
    peak = max(_conc(h / 2.0, dose_mg, v, ke) for h in range(0, 145))  # half-hour grid
    return points, round(peak, 2)


def _clearance_ratio(fm: float, ratio_i_ki: float) -> float:
    """Factor by which clearance falls: 1 / (1 + fm * [I]/Ki)."""
    return 1.0 + fm * ratio_i_ki


def _severity(factor: float) -> str:
    if factor >= 3.0:
        return "severe"
    if factor >= 1.5:
        return "moderate"
    if factor > 1.05:
        return "mild"
    return "none"


def pk_pd_simulation(patient_id: str) -> dict:
    patient = get_patient(patient_id)
    rules = _load("cyp450_interactions.json")
    perp = rules["perpetrators"][patient["new_rx"]["perpetrator_id"]]
    sim_rules = rules["safe_dose_rules"]

    ratio = 0.0 if not perp["ki_uM"] else perp["plasma_conc_uM"] / perp["ki_uM"]

    # Per-victim impact (graph edges)
    victims = []
    for vid in patient["interaction_victims"]:
        vr = rules["victims"][vid]
        med = next((m for m in patient["medications"] if m.get("id") == vid), {})
        factor = _clearance_ratio(vr["fm"], ratio) if perp["enzyme"] == vr["enzyme"] else 1.0
        victims.append({
            "id": vid,
            "label": med.get("label", vr["name"]),
            "name": vr["name"],
            "exposure_increase_x": round(factor, 2),
            "severity": _severity(factor),
        })

    # Simulated victim: the drug whose 72 h curve is shown
    sv = rules["victims"][patient["simulated_victim"]]
    factor = _clearance_ratio(sv["fm"], ratio) if perp["enzyme"] == sv["enzyme"] else 1.0
    ke_base = sv["ke_baseline_per_h"]
    ke_inh = ke_base / factor

    baseline, peak_base = _curve(sv["dose_mg"], sv, ke_base)
    original, peak_orig = _curve(sv["dose_mg"], sv, ke_inh)

    threshold = sv["toxicity_threshold"]
    target = sim_rules["target_peak_fraction_of_threshold"] * threshold

    def steady_state_peak(dose, ke):
        return max(_conc(480 + h / 2.0, dose, sv, ke) for h in range(0, 2 * sv["interval_h"] + 1))

    multiplier = 1.0
    if peak_orig > target or steady_state_peak(sv["dose_mg"], ke_inh) > threshold:
        m = 1.0
        while m > sim_rules["multiplier_floor"]:
            m = round(m - sim_rules["multiplier_step"], 2)
            if steady_state_peak(sv["dose_mg"] * m, ke_inh) <= target:
                break
        multiplier = m
    step = sv["dose_step"]
    adj_dose = max(step, round(sv["dose_mg"] * multiplier / step) * step) if multiplier < 1.0 else sv["dose_mg"]
    multiplier = round(adj_dose / sv["dose_mg"], 3)
    adjusted, peak_adj = _curve(adj_dose, sv, ke_inh)

    breach = peak_orig > threshold
    saturated = perp["enzyme"] is not None and factor >= 3.0
    overall = max((v["severity"] for v in victims), key=["none", "mild", "moderate", "severe"].index, default="none")
    if breach:
        overall = "severe"

    nodes = [{"id": "rx", "kind": "rx", "label": "New Rx", "sub": patient["new_rx"]["name"]}]
    edges = []
    if perp["enzyme"]:
        nodes.append({"id": "enzyme", "kind": "enzyme", "label": perp["enzyme"], "sub": "saturated" if saturated else "competing", "saturated": saturated})
        edges.append({"from": "rx", "to": "enzyme", "label": "inhibits", "severity": "severe" if saturated else "mild"})
        for v in victims:
            nodes.append({"id": v["id"], "kind": "victim", "label": v["label"], "sub": v["name"], "severity": v["severity"]})
            edges.append({"from": "enzyme", "to": v["id"], "label": f"{v['exposure_increase_x']}x exposure", "severity": v["severity"]})
    else:
        nodes.append({"id": "none", "kind": "none", "label": "No CYP pathway", "sub": "no enzyme competition"})
        edges.append({"from": "rx", "to": "none", "label": "none", "severity": "none"})

    return {
        "tool": "pk_pd_simulation_tool",
        "patient_id": patient_id,
        "perpetrator": perp["name"],
        "enzyme": perp["enzyme"],
        "enzyme_saturation": "saturated" if saturated else ("partial" if perp["enzyme"] and factor > 1.05 else "none"),
        "interaction_severity": overall,
        "victim_drug": sv["name"],
        "clearance_reduction_factor": round(factor, 2),
        "hours": HOURS,
        "baseline": baseline,
        "original": original,
        "adjusted": adjusted,
        "unit": sv["unit"],
        "toxicity_threshold": threshold,
        "therapeutic_window": sv["therapeutic_window"],
        "peak_original": peak_orig,
        "peak_adjusted": peak_adj,
        "peak_baseline": peak_base,
        "threshold_breached_original": breach,
        "threshold_breached_adjusted": peak_adj > threshold,
        "original_dose_mg": sv["dose_mg"],
        "adjusted_dose_mg": adj_dose,
        "dose_multiplier": multiplier,
        "interval_h": sv["interval_h"],
        "dose_adjusted": multiplier < 1.0,
        "interaction_graph": {"nodes": nodes, "edges": edges},
        "victims": victims,
    }


# --------------------------------------------------------------------------- #
# 2. PA Resolver: payer policy lookup + FHIR Claim
# --------------------------------------------------------------------------- #
def _evaluate(criterion: dict, patient: dict, interaction_review_complete: bool):
    chk = criterion["check"]
    if chk == "dx_code":
        ok = patient["diagnosis"]["code"] == criterion["equals"]
        return ok, f"Chart diagnosis {patient['diagnosis']['code']}: {patient['diagnosis']['text']}"
    if chk == "lab_gt":
        val = patient["labs"].get(criterion["lab"])
        return (val is not None and val > criterion["value"]), f"{criterion['lab']} = {val}"
    if chk == "interaction_review":
        return interaction_review_complete, "Clinical Sentinel 72-hour simulation and dose plan attached"
    if chk == "step_weeks":
        best = max(patient["prior_therapy"], key=lambda t: t["weeks"], default=None)
        if not best:
            return False, "No prior therapy documented"
        return best["weeks"] >= criterion["min_weeks"], f"{best['drug']} for {best['weeks']} weeks, {best['outcome']} (note {best['note_date']})"
    if chk == "flag":
        val = bool(patient["chart_flags"].get(criterion["flag"]))
        return val, f"Chart flag {criterion['flag']} = {val}"
    return False, "Unknown check"


def payer_policy_lookup(patient_id: str, interaction_review_complete: bool = True) -> dict:
    patient = get_patient(patient_id)
    book = _load("payer_policies.json")
    perp_id = patient["new_rx"]["perpetrator_id"]
    pol_id, pol = next((k, v) for k, v in book["policies"].items() if v["applies_to"] == perp_id)
    sec = pol["criteria_section"]

    results = []
    for c in pol["criteria"]:
        ok, evidence = _evaluate(c, patient, interaction_review_complete)
        results.append({"id": c["id"], "text": c["text"], "met": ok, "evidence": evidence})
    all_met = all(r["met"] for r in results)
    citation = f"Source: {pol['document']}, section {sec} ({pol['sections'][sec]})"

    today = datetime.now(timezone.utc).date()
    appt = today + timedelta(days=patient["days_until_appointment"])
    claim = json.loads(json.dumps(book["fhir_claim_template"]))
    claim.update({
        "id": f"claim-{patient_id.lower()}",
        "created": today.isoformat(),
        "patient": {"reference": f"Patient/{patient_id}", "display": patient["name"]},
        "insurer": {"reference": f"Organization/{book['payer']['fhir_org_id']}", "display": book["payer"]["name"]},
        "provider": {"reference": "Organization/org-healthsync-demo", "display": "HealthSync demo clinic"},
        "diagnosis": [{
            "sequence": 1,
            "diagnosisCodeableConcept": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": patient["diagnosis"]["code"], "display": patient["diagnosis"]["text"]}]},
        }],
        "supportingInfo": [
            {"sequence": i + 1, "category": {"text": r["id"]}, "valueString": r["evidence"]}
            for i, r in enumerate(results)
        ],
        "item": [{
            "sequence": 1,
            "productOrService": {"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": patient["new_rx"]["cpt"] or "J3490", "display": f"{patient['new_rx']['name']} ({patient['new_rx']['regimen']})"}]},
            "servicedDate": appt.isoformat(),
        }],
        "insurance": [{"sequence": 1, "focal": True, "coverage": {"reference": f"Coverage/cov-{patient_id.lower()}"}}],
    })

    letter = (
        f"Re: Prior authorization for {patient['new_rx']['name']} ({patient['new_rx']['regimen']}), {patient['name']}, "
        f"{patient['age']}{patient['sex']}.\n\n"
        f"Diagnosis: {patient['diagnosis']['text']} ({patient['diagnosis']['code']}).\n"
        f"Policy matched: {pol['title']}, {pol['document']}, section {sec}.\n\n"
        + "\n".join(f"- {'Met' if r['met'] else 'NOT MET'}: {r['text']}. Evidence: {r['evidence']}." for r in results)
        + "\n\nThis is synthetic demo content generated from sample data."
    )

    return {
        "tool": "payer_policy_lookup_tool",
        "patient_id": patient_id,
        "payer": book["payer"]["name"],
        "policy_id": pol_id,
        "policy_title": pol["title"],
        "document": pol["document"],
        "section": sec,
        "section_title": pol["sections"][sec],
        "citation": citation,
        "codes": pol["codes"],
        "criteria": results,
        "all_criteria_met": all_met,
        "claim": claim,
        "justification_letter": letter,
    }


def build_claim_response(patient_id: str) -> dict:
    return {
        "resourceType": "ClaimResponse",
        "id": f"cr-{patient_id.lower()}-0001",
        "status": "active",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "professional"}]},
        "use": "preauthorization",
        "patient": {"reference": f"Patient/{patient_id}"},
        "created": now_iso(),
        "insurer": {"reference": "Organization/org-northwind"},
        "request": {"reference": f"Claim/claim-{patient_id.lower()}"},
        "outcome": "complete",
        "disposition": "Approved (simulated)",
        "preAuthRef": f"PA-{patient_id[3:]}-SIM-0001",
    }


# --------------------------------------------------------------------------- #
# 3. Supply Chain Orchestrator: inventory + X12 EDI 850 / 855
# --------------------------------------------------------------------------- #
def _x12(segments: list) -> str:
    return "~\n".join(segments) + "~"


def build_edi_850(patient_id: str, item: dict, qty: int, now: datetime, control: int = 1) -> str:
    ymd, hm = now.strftime("%y%m%d"), now.strftime("%H%M")
    ymd4 = now.strftime("%Y%m%d")
    po = f"PO{patient_id[3:]}{control:04d}"
    body = [
        "ST*850*0001",
        f"BEG*00*SA*{po}**{ymd4}",
        f"REF*IA*{item['supplier']['edi_id']}",
        f"DTM*002*{(now + timedelta(hours=item['supplier']['lead_time_hours'])).strftime('%Y%m%d')}",
        "N1*BY*HEALTHSYNC DEMO CLINIC*92*HSOS01",
        f"N1*SE*{item['supplier']['name'].upper()}*92*{item['supplier']['edi_id']}",
        f"PO1*1*{qty}*EA*{item['unit_price_usd']:.2f}**N4*{item['ndc'].replace('-', '')}",
        f"PID*F****{item['product'].upper()}",
        "CTT*1",
    ]
    body.append(f"SE*{len(body) + 1}*0001")
    segs = [
        f"ISA*00*{'':10}*00*{'':10}*ZZ*{'HEALTHSYNCOS':<15}*ZZ*{item['supplier']['edi_id']:<15}*{ymd}*{hm}*U*00401*{control:09d}*0*T*:",
        f"GS*PO*HEALTHSYNCOS*{item['supplier']['edi_id']}*{ymd4}*{hm}*{control}*X*004010",
        *body,
        f"GE*1*{control}",
        f"IEA*1*{control:09d}",
    ]
    return _x12(segs)


def build_edi_855(patient_id: str, item: dict, qty: int, now: datetime, control: int = 2) -> str:
    ymd, hm = now.strftime("%y%m%d"), now.strftime("%H%M")
    ymd4 = now.strftime("%Y%m%d")
    po = f"PO{patient_id[3:]}0001"
    eta = (now + timedelta(hours=item["supplier"]["lead_time_hours"])).strftime("%Y%m%d")
    body = [
        "ST*855*0001",
        f"BAK*00*AD*{po}*{ymd4}",
        f"PO1*1*{qty}*EA*{item['unit_price_usd']:.2f}**N4*{item['ndc'].replace('-', '')}",
        f"ACK*IA*{qty}*EA*068*{eta}",
        "CTT*1",
    ]
    body.append(f"SE*{len(body) + 1}*0001")
    segs = [
        f"ISA*00*{'':10}*00*{'':10}*ZZ*{item['supplier']['edi_id']:<15}*ZZ*{'HEALTHSYNCOS':<15}*{ymd}*{hm}*U*00401*{control:09d}*0*T*:",
        f"GS*PR*{item['supplier']['edi_id']}*HEALTHSYNCOS*{ymd4}*{hm}*{control}*X*004010",
        *body,
        f"GE*1*{control}",
        f"IEA*1*{control:09d}",
    ]
    return _x12(segs)


def inventory_edi(patient_id: str) -> dict:
    patient = get_patient(patient_id)
    item = _load("specialty_inventory.json")["items"][patient_id]
    now = datetime.now(timezone.utc)
    coverage = round(item["stock_units"] / item["required_units"] * 100)
    shortfall = max(0, item["required_units"] - item["stock_units"])
    qty = shortfall  # order up to the full required quantity
    lead_h = item["supplier"]["lead_time_hours"]
    eta = now + timedelta(hours=lead_h)
    appt = now + timedelta(days=patient["days_until_appointment"])
    stockout_risk = item["stock_days"] < patient["days_until_appointment"]
    return {
        "tool": "inventory_edi_tool",
        "patient_id": patient_id,
        "ndc": item["ndc"],
        "product": item["product"],
        "unit": item["unit"],
        "stock_units": item["stock_units"],
        "required_units": item["required_units"],
        "stock_days": item["stock_days"],
        "days_until_appointment": patient["days_until_appointment"],
        "appointment_date": appt.date().isoformat(),
        "reorder_threshold_units": item["reorder_threshold_units"],
        "below_reorder_threshold": item["stock_units"] < item["reorder_threshold_units"],
        "coverage_pct": coverage,
        "stockout_risk": stockout_risk,
        "supplier": item["supplier"],
        "order_quantity": qty,
        "order_total_usd": round(qty * item["unit_price_usd"], 2),
        "eta": eta.isoformat(timespec="seconds"),
        "eta_before_appointment": eta <= appt,
        "edi_850": {"status": "Queued", "raw": build_edi_850(patient_id, item, qty, now)},
        "edi_855": {"status": "Pending", "raw": None},
    }


# --------------------------------------------------------------------------- #
# CrewAI tool wrappers (what the agents actually call)
# --------------------------------------------------------------------------- #
def _brief(result: dict, keys: list) -> str:
    """Agents get a compact summary; the full payload stays server-side."""
    return json.dumps({k: result[k] for k in keys})


@tool("pk_pd_simulation_tool")
def pk_pd_simulation_tool(patient_id: str) -> str:
    """Run the deterministic 72-hour pharmacokinetic simulation for a patient id (for example PT-1042).
    Returns interaction severity, enzyme saturation, peak concentrations against the toxicity
    threshold, and the recommended dose adjustment."""
    r = pk_pd_simulation(patient_id)
    return _brief(r, [
        "victim_drug", "enzyme", "enzyme_saturation", "interaction_severity", "clearance_reduction_factor",
        "toxicity_threshold", "unit", "peak_original", "peak_adjusted", "threshold_breached_original",
        "threshold_breached_adjusted", "original_dose_mg", "adjusted_dose_mg", "interval_h", "dose_adjusted",
    ])


@tool("payer_policy_lookup_tool")
def payer_policy_lookup_tool(patient_id: str) -> str:
    """Look up the payer policy for the patient's new prescription, verify each clinical criterion
    against the chart, cite the policy section, and build the FHIR R4 Claim for prior authorization."""
    r = payer_policy_lookup(patient_id)
    return _brief(r, ["payer", "policy_title", "citation", "all_criteria_met", "criteria"])


@tool("inventory_edi_tool")
def inventory_edi_tool(patient_id: str) -> str:
    """Compare specialty inventory against the patient's appointment, compute supply coverage,
    and draft a queued X12 EDI 850 purchase order."""
    r = inventory_edi(patient_id)
    return _brief(r, [
        "product", "stock_units", "required_units", "coverage_pct", "stock_days",
        "days_until_appointment", "stockout_risk", "order_quantity", "eta", "eta_before_appointment",
    ])
