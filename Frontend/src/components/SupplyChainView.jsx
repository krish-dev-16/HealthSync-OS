import Pill from "./Pill.jsx";
import { coverageColor } from "./SupplyCard.jsx";

function Timeline({ supply }) {
  const apptDay = supply.days_until_appointment;
  const etaDay = Math.max(0.1, Math.round(((new Date(supply.eta) - Date.now()) / 86400000) * 10) / 10);
  const span = Math.max(apptDay, supply.stock_days, etaDay) * 1.15;
  const pct = (d) => `${(d / span) * 100}%`;
  const short = supply.stock_days < apptDay;
  return (
    <div>
      <div className="timeline" role="img"
           aria-label={`Stock lasts ${supply.stock_days} days. The appointment is in ${apptDay} days. The order arrives in about ${etaDay} days.`}>
        <div className="tl-bar" style={{ width: pct(supply.stock_days), background: short ? "#B42318" : "#0F766E" }} />
        <div className={`tl-mark tl-appt${apptDay / span > 0.6 ? " flip" : ""}`} style={{ left: pct(apptDay) }}><span>Appointment, day {apptDay}</span></div>
        <div className={`tl-mark tl-eta${etaDay / span > 0.6 ? " flip" : ""}`} style={{ left: pct(etaDay) }}><span>Order ETA, day {etaDay}</span></div>
      </div>
      <p className="small muted tl-note">
        Bar = days of supply on hand ({supply.stock_days}). {short ? "Stock runs out before the appointment, so the order is time-critical." : "Stock lasts through the appointment."}{" "}
        {supply.eta_before_appointment ? "The queued order is expected to arrive in time." : "The order is expected to arrive after the appointment."}
      </p>
    </div>
  );
}

export default function SupplyChainView({ state }) {
  const s = state.supply;
  return (
    <div className="stack">
      <section className="card">
        <div className="row spread">
          <div>
            <h2>NDC inventory</h2>
            <p className="sub flush">{s.product}</p>
          </div>
          <div className="row">
            {s.rows.map((r) => <Pill key={r.label} tone={r.tone}>{r.label.replace(" purchase order", "")}: {r.text}</Pill>)}
          </div>
        </div>
        <table className="diff wide">
          <tbody>
            <tr><th scope="row">NDC</th><td>{s.ndc}</td></tr>
            <tr><th scope="row">Stock</th><td>{s.stock_units} of {s.required_units} {s.unit}s required</td></tr>
            <tr>
              <th scope="row">Coverage</th>
              <td><b style={{ color: coverageColor(s.coverage_pct) }}>{s.coverage_pct}%</b>{s.below_reorder_threshold ? ` · below reorder threshold (${s.reorder_threshold_units})` : ""}</td>
            </tr>
            <tr><th scope="row">Supplier</th><td>{s.supplier.name} ({s.supplier.edi_id}), {s.supplier.lead_time_hours} h lead time</td></tr>
            <tr><th scope="row">Order</th><td>{s.order_quantity} {s.unit}s · ${s.order_total_usd.toLocaleString()} · ETA {s.eta.slice(0, 10)}</td></tr>
          </tbody>
        </table>
        <p className="small muted">{s.coverage_summary} {s.summary}</p>
      </section>

      <section className="card">
        <h2>Days of supply vs. appointment</h2>
        <p className="sub">Appointment on {s.appointment_date}</p>
        <Timeline supply={s} />
      </section>

      <section className="card">
        <h2>X12 EDI 850 purchase order · {s.edi_850.status}</h2>
        <pre className="code" tabIndex={0}>{s.edi_850.raw}</pre>
      </section>

      <section className="card">
        <h2>X12 EDI 855 acknowledgment · {s.edi_855.status}</h2>
        {s.edi_855.raw ? (
          <pre className="code" tabIndex={0}>{s.edi_855.raw}</pre>
        ) : (
          <p className="small muted">No acknowledgment yet. The supplier responds after the purchase order is dispatched.</p>
        )}
      </section>
    </div>
  );
}
