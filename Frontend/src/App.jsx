import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Pill from "./components/Pill.jsx";
import InteractionGraph from "./components/InteractionGraph.jsx";
import SimulationChart from "./components/SimulationChart.jsx";
import PAStepper from "./components/PAStepper.jsx";
import SupplyCard from "./components/SupplyCard.jsx";
import AgentTrace from "./components/AgentTrace.jsx";
import ReviewModal from "./components/ReviewModal.jsx";
import AuthorizationView from "./components/AuthorizationView.jsx";
import SupplyChainView from "./components/SupplyChainView.jsx";
import AuditView from "./components/AuditView.jsx";

const TABS = [
  { id: "safety", label: "Clinical Safety" },
  { id: "auth", label: "Authorization" },
  { id: "supply", label: "Supply Chain" },
  { id: "audit", label: "Audit Trail" },
];

export default function App() {
  const [tab, setTab] = useState("safety");
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState(null);
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(null); // "run" | "approve" | "load" | null
  const [error, setError] = useState(null);
  const [showReview, setShowReview] = useState(false);

  const guard = useCallback(async (kind, fn) => {
    setBusy(kind);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(null);
    }
  }, []);

  useEffect(() => {
    guard("load", async () => {
      const list = await api.patients();
      setPatients(list);
      setPatientId(list[0].id);
    });
  }, [guard]);

  useEffect(() => {
    if (!patientId) return;
    guard("load", async () => setState(await api.workflow(patientId)));
  }, [patientId, guard]);

  const run = () => guard("run", async () => setState(await api.run(patientId)));
  const approve = () => guard("approve", async () => setState(await api.approve(patientId)));
  const reset = () => guard("load", async () => setState(await api.reset(patientId)));

  const approved = state?.status === "approved";
  const modeText = !state
    ? ""
    : state.mode === "crewai_live"
    ? `Live CrewAI run (${state.model_used})`
    : state.llm_note || "Template text";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">HealthSync OS</div>
        <nav aria-label="Main">
          {TABS.map((t) => (
            <button key={t.id} className="nav" aria-current={tab === t.id ? "page" : undefined} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main">
        <div className="row header">
          <div>
            <h1>Prescription workflow</h1>
            <p className="sub flush">
              {state
                ? `Synthetic patient · ${state.patient.medication_count} active medications · all figures are sample data`
                : "Loading…"}
            </p>
          </div>
          {state && <Pill tone={state.header_badge.tone}>{state.header_badge.label}</Pill>}
        </div>

        <div className="card controls">
          <label className="field">
            <span className="small muted">Patient case</span>
            <select value={patientId || ""} onChange={(e) => setPatientId(e.target.value)} disabled={!!busy}>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>{p.id} · {p.label}</option>
              ))}
            </select>
          </label>
          <button className="btn btn--primary" onClick={run} disabled={!!busy || !patientId}>
            {busy === "run" ? (<><span className="spinner" aria-hidden="true" /> Running agents…</>) : "Run CrewAI Pipeline"}
          </button>
          <button className="link" onClick={reset} disabled={!!busy || !patientId}>Reset case</button>
          <p className="small muted mode" aria-live="polite">{busy === "run" ? "The three agents run in sequence and can take a minute with a free-tier key." : modeText}</p>
        </div>

        {error && <div className="alert" role="alert">Something went wrong: {error}</div>}

        {state && tab === "safety" && (
          <>
            <div className="card pipeline">
              <div className="row stages">
                {state.stages.map((s) => (
                  <div key={s.label}>
                    <div className="stage-label">{s.label}</div>
                    <Pill tone={s.tone}>{s.text}</Pill>
                  </div>
                ))}
              </div>
              <div className="row">
                <button className="btn btn--primary" onClick={approve} disabled={approved || !!busy}>
                  {busy === "approve" ? "Submitting…" : approved ? "Approved" : "Approve and submit"}
                </button>
                <button className="btn btn--secondary" onClick={() => setShowReview(true)}>Review changes</button>
              </div>
            </div>

            <div className="grid">
              <section className="card c7">
                <h2>Interaction graph</h2>
                <p className="sub">{state.interaction.subtitle}</p>
                <InteractionGraph interaction={state.interaction} />
              </section>
              <section className="card c5">
                <h2>72-hour concentration simulation</h2>
                <p className="sub">{state.simulation.victim_drug} · hepatic, renal and cardiac models, sample output</p>
                <SimulationChart sim={state.simulation} />
              </section>
              <section className="card c4">
                <h2>Prior authorization</h2>
                <p className="sub">Da Vinci FHIR submission</p>
                <PAStepper steps={state.prior_auth.steps} />
              </section>
              <section className="card c4">
                <h2>Supply</h2>
                <p className="sub">{state.supply.product} · days of supply vs. appointment</p>
                <SupplyCard supply={state.supply} />
              </section>
              <section className="card c4">
                <h2>Agent trace</h2>
                <p className="sub">Live decisions with sources</p>
                <AgentTrace trace={state.agent_trace} />
              </section>
            </div>
          </>
        )}
        {state && tab === "auth" && <AuthorizationView state={state} />}
        {state && tab === "supply" && <SupplyChainView state={state} />}
        {state && tab === "audit" && <AuditView state={state} />}
      </main>

      {showReview && state && (
        <ReviewModal state={state} busy={!!busy} onClose={() => setShowReview(false)} onApprove={approve} />
      )}
    </div>
  );
}
