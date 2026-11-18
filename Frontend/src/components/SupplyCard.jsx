import Pill from "./Pill.jsx";

export function coverageColor(pct) {
  if (pct < 30) return "#B42318";
  if (pct < 70) return "#B45309";
  return "#0F766E";
}

export default function SupplyCard({ supply }) {
  const pct = Math.min(100, supply.coverage_pct);
  return (
    <>
      <div
        className="bar"
        role="img"
        aria-label={`Stock covers ${supply.coverage_pct} percent of the quantity needed by the appointment`}
      >
        <div className="bar-fill" style={{ width: `${pct}%`, background: coverageColor(pct) }} />
      </div>
      <div className="row spread small muted bar-labels">
        <span>Current stock ({supply.coverage_pct}%)</span>
        <span>Needed by appointment</span>
      </div>
      <p className="small muted supply-meta">
        {supply.stock_units} of {supply.required_units} {supply.unit}s · {supply.stock_days} days of supply · appointment in{" "}
        {supply.days_until_appointment} days
        {supply.stockout_risk && <b className="red"> · stockout risk</b>}
      </p>
      <div className="supply-list">
        {supply.rows.map((r) => (
          <div key={r.label}>
            <span>{r.label}</span>
            <Pill tone={r.tone}>{r.text}</Pill>
          </div>
        ))}
      </div>
    </>
  );
}
