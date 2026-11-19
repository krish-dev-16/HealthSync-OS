import Pill from "./Pill.jsx";

export default function AuthorizationView({ state }) {
  const pa = state.prior_auth;
  return (
    <div className="stack">
      <section className="card">
        <div className="row spread">
          <div>
            <h2>Policy match</h2>
            <p className="sub flush">{pa.payer} · {pa.policy_title}</p>
          </div>
          <Pill tone={pa.status === "Approved" ? "ok" : pa.all_criteria_met ? "info" : "warn"}>{pa.status}</Pill>
        </div>
        <p className="cite">{pa.citation}</p>
        <p className="small muted">ICD-10 {pa.codes.icd10.join(", ")}{pa.codes.cpt.length ? ` · CPT ${pa.codes.cpt.join(", ")}` : ""}</p>
        <ul className="criteria">
          {pa.criteria.map((c) => (
            <li key={c.id}>
              <Pill tone={c.met ? "ok" : "warn"}>{c.met ? "Met" : "Not met"}</Pill>
              <span>{c.text}<span className="small muted block">{c.evidence}</span></span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Clinical justification letter</h2>
        <p className="sub">Written by the PA Resolver from the chart and the Sentinel's dose plan</p>
        <pre className="letter">{pa.justification_letter}</pre>
      </section>

      <section className="card">
        <h2>Da Vinci PAS · FHIR R4 Claim</h2>
        <p className="sub">Draft payload, sent only after clinician approval</p>
        <pre className="code" tabIndex={0}>{JSON.stringify(pa.claim, null, 2)}</pre>
      </section>

      {pa.claim_response && (
        <section className="card">
          <h2>FHIR ClaimResponse</h2>
          <p className="sub">Simulated payer decision</p>
          <pre className="code" tabIndex={0}>{JSON.stringify(pa.claim_response, null, 2)}</pre>
        </section>
      )}
    </div>
  );
}
