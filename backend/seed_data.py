"""Generates the synthetic JSON datasets used by HealthSync OS.

Everything here is fictional and deterministic. Run directly (`python seed_data.py`)
or let `main.py` call `ensure_seed_data()` on startup. Existing files are kept,
pass force=True (or `--force` on the command line) to regenerate them.
"""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# --------------------------------------------------------------------------- #
# CYP450 rules: perpetrators (inhibitors), victims (substrates) and PK params
# --------------------------------------------------------------------------- #
CYP450 = {
    "_note": "Synthetic, illustrative values only. Not for clinical use.",
    "perpetrators": {
        "ritonavir_boosted": {
            "name": "Drug A (ritonavir-boosted regimen)",
            "enzyme": "CYP3A4",
            "mechanism": "strong mechanism-based inhibitor",
            "ki_uM": 0.05,
            "plasma_conc_uM": 0.30,
        },
        "biologic_none": {
            "name": "Drug A (biologic)",
            "enzyme": None,
            "mechanism": "no cytochrome P450 involvement",
            "ki_uM": None,
            "plasma_conc_uM": 0.0,
        },
        "amlodipine_weak": {
            "name": "Drug A (formulary-preferred agent)",
            "enzyme": "CYP3A4",
            "mechanism": "weak competitive inhibitor",
            "ki_uM": 3.0,
            "plasma_conc_uM": 1.0,
        },
    },
    "victims": {
        "tacrolimus": {
            "name": "Tacrolimus",
            "enzyme": "CYP3A4",
            "fm": 0.95,
            "narrow_therapeutic_index": True,
            "unit": "ng/mL",
            "toxicity_threshold": 20.0,
            "therapeutic_window": [5.0, 15.0],
            "dose_mg": 1.2,
            "interval_h": 12,
            "bioavailability": 0.25,
            "volume_L": 62.0,
            "ke_baseline_per_h": 0.04,
            "ka_per_h": 1.0,
            "dose_step": 0.05,
        },
        "atorvastatin": {
            "name": "Atorvastatin",
            "enzyme": "CYP3A4",
            "fm": 0.70,
            "narrow_therapeutic_index": False,
            "unit": "ng/mL",
            "toxicity_threshold": 25.0,
            "therapeutic_window": [2.0, 15.0],
            "dose_mg": 20.0,
            "interval_h": 24,
            "bioavailability": 0.14,
            "volume_L": 381.0,
            "ke_baseline_per_h": 0.05,
            "ka_per_h": 1.2,
            "dose_step": 0.25,
        },
        "amlodipine": {
            "name": "Amlodipine",
            "enzyme": "CYP3A4",
            "fm": 0.90,
            "narrow_therapeutic_index": False,
            "unit": "ng/mL",
            "toxicity_threshold": 30.0,
            "therapeutic_window": [3.0, 20.0],
            "dose_mg": 5.0,
            "interval_h": 24,
            "bioavailability": 0.64,
            "volume_L": 1500.0,
            "ke_baseline_per_h": 0.02,
            "ka_per_h": 0.2,
            "dose_step": 0.25,
        },
        "simvastatin": {
            "name": "Simvastatin",
            "enzyme": "CYP3A4",
            "fm": 0.80,
            "narrow_therapeutic_index": False,
            "unit": "ng/mL",
            "toxicity_threshold": 25.0,
            "therapeutic_window": [1.0, 15.0],
            "dose_mg": 20.0,
            "interval_h": 24,
            "bioavailability": 0.05,
            "volume_L": 300.0,
            "ke_baseline_per_h": 0.2,
            "ka_per_h": 1.5,
            "dose_step": 0.25,
        },
    },
    "safe_dose_rules": {
        "target_peak_fraction_of_threshold": 0.8,
        "multiplier_floor": 0.1,
        "multiplier_step": 0.05,
    },
}

# --------------------------------------------------------------------------- #
# Payer policies (Section 3 holds the clinical criteria) + FHIR Claim template
# --------------------------------------------------------------------------- #
PAYER_POLICIES = {
    "_note": "Fictional payer. Policy text is synthetic.",
    "payer": {"id": "PAYER-NWH", "name": "Northwind Health Plan", "fhir_org_id": "org-northwind"},
    "policies": {
        "POL-ART-01": {
            "title": "Boosted antiretroviral regimen, Clinical Policy Bulletin",
            "document": "Northwind CPB-ART-01",
            "applies_to": "ritonavir_boosted",
            "codes": {"icd10": ["B20", "Z94.0"], "cpt": ["96365"]},
            "sections": {
                "1": "Scope and definitions",
                "2": "Coverage determination process",
                "3": "Clinical criteria for approval",
                "4": "Appeals and peer-to-peer review",
            },
            "criteria_section": "3",
            "criteria": [
                {"id": "dx", "text": "Confirmed HIV-1 diagnosis (ICD-10 B20) documented in chart", "check": "dx_code", "equals": "B20"},
                {"id": "vl", "text": "HIV-1 RNA above 200 copies/mL in the last 90 days", "check": "lab_gt", "lab": "hiv_rna_copies_ml", "value": 200},
                {"id": "ddi", "text": "Documented drug-interaction review with dose plan for narrow-therapeutic-index co-medications", "check": "interaction_review"},
            ],
        },
        "POL-BIO-02": {
            "title": "TNF-inhibitor biologics for Crohn's disease, Clinical Policy Bulletin",
            "document": "Northwind CPB-BIO-02",
            "applies_to": "biologic_none",
            "codes": {"icd10": ["K50.90"], "cpt": ["96413"]},
            "sections": {
                "1": "Scope and definitions",
                "2": "Coverage determination process",
                "3": "Clinical criteria for approval (step therapy)",
                "4": "Appeals and peer-to-peer review",
            },
            "criteria_section": "3",
            "criteria": [
                {"id": "dx", "text": "Moderate to severe Crohn's disease (ICD-10 K50.90)", "check": "dx_code", "equals": "K50.90"},
                {"id": "step", "text": "Step therapy: at least 12 weeks of a conventional agent with inadequate response or intolerance", "check": "step_weeks", "min_weeks": 12},
                {"id": "tb", "text": "Negative tuberculosis screening within 12 months", "check": "flag", "flag": "tb_screen_negative_12mo"},
            ],
        },
        "POL-STD-03": {
            "title": "Formulary-preferred cardiovascular agents, Clinical Policy Bulletin",
            "document": "Northwind CPB-CV-03",
            "applies_to": "amlodipine_weak",
            "codes": {"icd10": ["I10"], "cpt": []},
            "sections": {
                "1": "Scope and definitions",
                "2": "Coverage determination process",
                "3": "Formulary status and clinical criteria",
                "4": "Appeals and peer-to-peer review",
            },
            "criteria_section": "3",
            "criteria": [
                {"id": "dx", "text": "Diagnosis of hypertension (ICD-10 I10)", "check": "dx_code", "equals": "I10"},
                {"id": "formulary", "text": "Agent is on the preferred formulary tier", "check": "flag", "flag": "formulary_preferred"},
            ],
        },
    },
    "fhir_claim_template": {
        "resourceType": "Claim",
        "meta": {"profile": ["http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-claim"]},
        "status": "active",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "professional"}]},
        "use": "preauthorization",
        "priority": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/processpriority", "code": "normal"}]},
    },
}

# --------------------------------------------------------------------------- #
# Specialty inventory
# --------------------------------------------------------------------------- #
INVENTORY = {
    "_note": "Synthetic inventory. NDC codes are made up.",
    "items": {
        "PT-1042": {
            "ndc": "00000-1042-01",
            "product": "Drug A specialty infusion kit",
            "unit": "kit",
            "stock_units": 8,
            "required_units": 20,
            "stock_days": 4,
            "reorder_threshold_units": 10,
            "unit_price_usd": 410.0,
            "supplier": {"name": "Meridian Specialty Distribution", "edi_id": "MERIDIAN01", "lead_time_hours": 24},
        },
        "PT-2089": {
            "ndc": "00000-2089-02",
            "product": "Drug A biologic prefilled pen",
            "unit": "pen",
            "stock_units": 3,
            "required_units": 20,
            "stock_days": 2,
            "reorder_threshold_units": 8,
            "unit_price_usd": 1325.0,
            "supplier": {"name": "Meridian Specialty Distribution", "edi_id": "MERIDIAN01", "lead_time_hours": 24},
        },
        "PT-3115": {
            "ndc": "00000-3115-03",
            "product": "Drug A 30-day pack",
            "unit": "pack",
            "stock_units": 17,
            "required_units": 20,
            "stock_days": 26,
            "reorder_threshold_units": 6,
            "unit_price_usd": 18.5,
            "supplier": {"name": "Meridian Specialty Distribution", "edi_id": "MERIDIAN01", "lead_time_hours": 24},
        },
    },
}

# --------------------------------------------------------------------------- #
# Synthetic patients
# --------------------------------------------------------------------------- #
PATIENTS = [
    {
        "id": "PT-1042",
        "label": "Case 1: High-risk CYP3A4 inhibition",
        "scenario": "Boosted antiretroviral starts for a kidney transplant recipient on tacrolimus",
        "name": "Synthetic Patient A",
        "age": 58,
        "sex": "M",
        "payer_id": "PAYER-NWH",
        "diagnosis": {"code": "B20", "text": "HIV disease, with transplant (Z94.0)"},
        "medications": [
            {"id": "tacrolimus", "label": "Drug B", "name": "Tacrolimus", "dose": "1.2 mg every 12 h"},
            {"id": "amlodipine", "label": "Drug C", "name": "Amlodipine", "dose": "5 mg daily"},
            {"id": "atorvastatin", "label": "Drug D", "name": "Atorvastatin", "dose": "20 mg daily"},
            {"name": "Mycophenolate", "dose": "500 mg twice daily"},
            {"name": "Prednisone", "dose": "5 mg daily"},
            {"name": "Lisinopril", "dose": "10 mg daily"},
            {"name": "Pantoprazole", "dose": "40 mg daily"},
        ],
        "new_rx": {"perpetrator_id": "ritonavir_boosted", "name": "Drug A", "regimen": "Ritonavir-boosted regimen", "dose": "per label, daily", "cpt": "96365"},
        "simulated_victim": "tacrolimus",
        "interaction_victims": ["tacrolimus", "amlodipine", "atorvastatin"],
        "labs": {"hiv_rna_copies_ml": 18400, "egfr": 54, "alt_u_l": 31},
        "chart_flags": {"tb_screen_negative_12mo": True, "formulary_preferred": False},
        "prior_therapy": [],
        "days_until_appointment": 10,
    },
    {
        "id": "PT-2089",
        "label": "Case 2: Specialty stockout and step-therapy PA",
        "scenario": "Crohn's disease biologic with 2 days of stock and a policy step-therapy requirement",
        "name": "Synthetic Patient B",
        "age": 41,
        "sex": "F",
        "payer_id": "PAYER-NWH",
        "diagnosis": {"code": "K50.90", "text": "Crohn's disease, unspecified"},
        "medications": [
            {"name": "Azathioprine", "dose": "100 mg daily (stopped, inadequate response)"},
            {"name": "Mesalamine", "dose": "2.4 g daily"},
            {"name": "Folic acid", "dose": "1 mg daily"},
            {"name": "Vitamin D3", "dose": "2000 IU daily"},
            {"name": "Omeprazole", "dose": "20 mg daily"},
            {"name": "Ferrous sulfate", "dose": "325 mg daily"},
            {"id": "atorvastatin", "label": "Drug B", "name": "Atorvastatin", "dose": "20 mg daily"},
        ],
        "new_rx": {"perpetrator_id": "biologic_none", "name": "Drug A", "regimen": "TNF-inhibitor biologic", "dose": "40 mg every 2 weeks", "cpt": "96413"},
        "simulated_victim": "atorvastatin",
        "interaction_victims": [],
        "labs": {"crp_mg_l": 38, "albumin_g_dl": 3.4},
        "chart_flags": {"tb_screen_negative_12mo": True, "formulary_preferred": False},
        "prior_therapy": [{"drug": "Azathioprine", "weeks": 14, "outcome": "inadequate response", "note_date": "2026-03-04"}],
        "days_until_appointment": 3,
    },
    {
        "id": "PT-3115",
        "label": "Case 3: Standard fast-track clearance",
        "scenario": "Formulary-preferred antihypertensive with a mild metabolic overlap",
        "name": "Synthetic Patient C",
        "age": 63,
        "sex": "F",
        "payer_id": "PAYER-NWH",
        "diagnosis": {"code": "I10", "text": "Essential hypertension"},
        "medications": [
            {"id": "simvastatin", "label": "Drug B", "name": "Simvastatin", "dose": "20 mg daily"},
            {"name": "Metformin", "dose": "500 mg twice daily"},
            {"name": "Aspirin", "dose": "81 mg daily"},
            {"name": "Levothyroxine", "dose": "75 mcg daily"},
            {"name": "Losartan", "dose": "50 mg daily"},
            {"name": "Calcium carbonate", "dose": "500 mg daily"},
            {"name": "Vitamin D3", "dose": "1000 IU daily"},
        ],
        "new_rx": {"perpetrator_id": "amlodipine_weak", "name": "Drug A", "regimen": "Formulary-preferred agent", "dose": "5 mg daily", "cpt": None},
        "simulated_victim": "simvastatin",
        "interaction_victims": ["simvastatin"],
        "labs": {"ldl_mg_dl": 112, "alt_u_l": 24},
        "chart_flags": {"tb_screen_negative_12mo": True, "formulary_preferred": True},
        "prior_therapy": [],
        "days_until_appointment": 14,
    },
]


def _write(name: str, payload, force: bool) -> bool:
    path = DATA_DIR / name
    if path.exists() and not force:
        return False
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return True


def ensure_seed_data(force: bool = False) -> list:
    """Create any missing dataset files. Returns the names that were written."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "patients.json": PATIENTS,
        "cyp450_interactions.json": CYP450,
        "payer_policies.json": PAYER_POLICIES,
        "specialty_inventory.json": INVENTORY,
    }
    return [name for name, payload in files.items() if _write(name, payload, force)]


if __name__ == "__main__":
    written = ensure_seed_data(force="--force" in sys.argv)
    print("Wrote:", ", ".join(written) if written else "nothing (files already exist)")
