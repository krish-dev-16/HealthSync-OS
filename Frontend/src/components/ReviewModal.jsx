import { useEffect, useRef } from "react";
import Pill from "./Pill.jsx";

export default function ReviewModal({ state, busy, onClose, onApprove }) {
  const ref = useRef(null);
  const approved = state.status === "approved";
  const { prescription: rx, simulation: sim, prior_auth: pa, supply } = state;

  useEffect(() => {
    const d = ref.current;
    if (d && !d.open) d.showModal();
    return () => d && d.open && d.close();
  }, []);

  const unit = sim.unit;
  const row = (label, a, b, bad) => (
    <tr>
      <th scope="row">{label}</th>
      <td className={bad ? "bad" : ""}>{a}</td>
      <td>{b}</td>
    </tr>
  );

  return (
    <dialog ref={ref} className="modal" onClose={onClose} onClick={(e) => e.target === ref.current && onClose()} aria-labelledby="review-title">
      <div className="modal-body">
        <div className="row spread">
          <h2 id="review-title" className="modal-title">Review changes</h2>
          <button className="link" onClick={onClose}>Close</button>
        </div>

        <section>
          <h3>Prescription: original vs. Sentinel-adjusted</h3>
          <table className="diff">
            <thead>
              <tr><th scope="col">{rx.drug}</th><th scope="col">Original</th><th scope="col">Sentinel-adjusted</th></tr>
            </thead>
            <tbody>
              {row("Dose", `${rx.original.dose_mg} mg`, `${rx.adjusted.dose_mg} mg`, false)}
              {row("Interval", `every ${rx.original.interval_h} h`, `every ${rx.adjusted.interval_h} h`, false)}
              {row("Peak, 72 h", `${sim.peak_original} ${unit}`, `${sim.peak_adjusted} ${unit}`, sim.threshold_breached_original)}
              {row("Toxicity threshold", `${sim.toxicity_threshold} ${unit}`, `${sim.toxicity_threshold} ${unit}`, false)}
              {row("Result", sim.threshold_breached_original ? "Exceeds threshold" : "Within threshold", sim.threshold_breached_adjusted ? "Exceeds threshold" : "Within threshold", sim.threshold_breached_original)}
            </tbody>
          </table>
          <p className="small muted">{rx.recommendation} {rx.rationale}</p>
        </section>

        <section>
          <h3>Matched payer policy</h3>
          <p className="cite">{pa.citation}</p>
          <ul className="criteria">
            {pa.criteria.map((c) => (
              <li key={c.id}>
                <Pill tone={c.met ? "ok" : "warn"}>{c.met ? "Met" : "Not met"}</Pill>
                <span>{c.text}<span className="small muted block">{c.evidence}</span></span>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3>EDI 850 purchase order ({supply.edi_850.status})</h3>
          <pre className="code">{supply.edi_850.raw}</pre>
        </section>

        <div className="row modal-actions">
          <button className="btn btn--secondary" onClick={onClose}>Close</button>
          <button className="btn btn--primary" disabled={approved || busy} onClick={async () => { await onApprove(); onClose(); }}>
            {approved ? "Approved" : "Approve and submit"}
          </button>
        </div>
      </div>
    </dialog>
  );
}
