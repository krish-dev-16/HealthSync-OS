const X0 = 40, X1 = 420, Y0 = 200, Y1 = 20;

export default function SimulationChart({ sim }) {
  const { hours, baseline, original, adjusted, toxicity_threshold: thr, unit, therapeutic_window: win } = sim;
  const showRed = sim.threshold_breached_original || JSON.stringify(original) !== JSON.stringify(adjusted);
  const all = [...baseline, ...original, ...adjusted];
  const yMax = Math.max(thr * 1.2, ...all) * 1.05;
  const x = (h) => X0 + (h / 72) * (X1 - X0);
  const y = (v) => Y0 - (v / yMax) * (Y0 - Y1);
  const path = (arr) => arr.map((v, i) => `${i ? "L" : "M"}${x(hours[i]).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const ticks = [0, 0.5, 1].map((f) => Math.round(yMax * f));

  const aria = sim.threshold_breached_original
    ? `Concentration of ${sim.victim_drug} over 72 hours: the original dose peaks at ${sim.peak_original} ${unit}, above the ${thr} ${unit} toxicity threshold. The adjusted dose peaks at ${sim.peak_adjusted} ${unit}, below it.`
    : `Concentration of ${sim.victim_drug} over 72 hours: peaks at ${sim.peak_original} ${unit}, well below the ${thr} ${unit} toxicity threshold.`;

  return (
    <>
      <svg viewBox="0 0 440 240" width="100%" role="img" aria-label={aria}>
        <rect x={X0} y={y(win[1])} width={X1 - X0} height={y(win[0]) - y(win[1])} fill="#E6F4F1" />
        <line x1={X0} y1={Y0} x2={X1} y2={Y0} stroke="#9AA9BC" />
        <line x1={X0} y1={Y1} x2={X0} y2={Y0} stroke="#9AA9BC" />
        {ticks.map((t) => (
          <text key={t} x={X0 - 6} y={y(t) + 4} fontSize="10" fill="#5B6B7F" textAnchor="end">{t}</text>
        ))}
        <text x="4" y="12" fontSize="10" fill="#5B6B7F">{unit}</text>
        <line x1={X0} y1={y(thr)} x2={X1} y2={y(thr)} stroke="#B45309" strokeDasharray="6 4" />
        <text x={X0 + 6} y={y(thr) - 6} fontSize="11" fill="#92400E">Toxicity threshold ({thr} {unit})</text>

        <path d={path(baseline)} fill="none" stroke="#5B6B7F" strokeWidth="2" strokeDasharray="3 3" />
        {showRed && <path d={path(original)} fill="none" stroke="#B42318" strokeWidth="3" />}
        <path d={path(showRed ? adjusted : original)} fill="none" stroke="#0F766E" strokeWidth="3" />
        {showRed &&
          adjusted.map((v, i) => <circle key={i} cx={x(hours[i])} cy={y(v)} r="2.5" fill="#0F766E" />)}

        {[0, 24, 48, 72].map((h) => (
          <text key={h} x={x(h)} y="218" fontSize="11" fill="#5B6B7F" textAnchor={h === 0 ? "start" : h === 72 ? "end" : "middle"}>{h}h</text>
        ))}
      </svg>
      <div className="row legend">
        {showRed ? (
          <>
            <span><b className="red">Red</b> original dose</span>
            <span><b className="teal">Teal with dots</b> adjusted dose</span>
          </>
        ) : (
          <span><b className="teal">Teal</b> current dose with new Rx</span>
        )}
        <span><b>Dashed grey</b> baseline without new Rx</span>
        <span><b className="band">Green band</b> therapeutic window</span>
      </div>
    </>
  );
}
