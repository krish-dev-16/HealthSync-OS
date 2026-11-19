const KIND = { tool_call: "Tool call", citation: "Citation", agent_output: "Agent output", agent_step: "Agent step", clinician: "Clinician", system: "System" };

export default function AuditView({ state }) {
  return (
    <section className="card">
      <h2>Audit trail</h2>
      <p className="sub">
        Append-only log of every agent step, tool calculation, source citation and clinician sign-off. Each entry carries the previous entry's hash, so a
        changed entry would break the chain. Mode: {state.mode === "crewai_live" ? `live CrewAI (${state.model_used})` : "template text"}.
      </p>
      <div className="table-wrap">
        <table className="audit">
          <thead>
            <tr><th scope="col">#</th><th scope="col">Time (UTC)</th><th scope="col">Actor</th><th scope="col">Type</th><th scope="col">Action</th><th scope="col">Detail</th><th scope="col">Source</th><th scope="col">Hash</th></tr>
          </thead>
          <tbody>
            {state.audit_trail.map((a) => (
              <tr key={a.seq}>
                <td>{a.seq}</td>
                <td className="nowrap">{a.timestamp.slice(11, 19)}</td>
                <td>{a.actor}</td>
                <td>{KIND[a.kind] || a.kind}</td>
                <td>{a.action}</td>
                <td>{a.detail}</td>
                <td>{a.source}</td>
                <td className="mono" title={`previous: ${a.prev_hash}`}>{a.hash}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
