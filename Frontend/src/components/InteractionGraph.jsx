const SEV = {
  severe: { color: "#B42318", width: 3.5 },
  moderate: { color: "#B45309", width: 2.5 },
  mild: { color: "#0F766E", width: 2 },
  none: { color: "#9AA9BC", width: 1.5 },
};

const CX = 218, CY = 120, R = 34;
const VX = 330, VW = 100, VH = 40;

function victimYs(n) {
  if (n <= 1) return [120];
  const top = 46, bottom = 194;
  return Array.from({ length: n }, (_, i) => top + ((bottom - top) * i) / (n - 1));
}

export default function InteractionGraph({ interaction }) {
  const { nodes, edges } = interaction.graph;
  const enzyme = nodes.find((n) => n.kind === "enzyme");
  const none = nodes.find((n) => n.kind === "none");
  const victims = nodes.filter((n) => n.kind === "victim");
  const ys = victimYs(victims.length);
  const rxEdge = edges.find((e) => e.from === "rx");
  const rxStyle = SEV[rxEdge?.severity || "none"];

  const aria = enzyme
    ? `The new prescription inhibits ${enzyme.label}, ${enzyme.saturated ? "saturating it and " : ""}raising exposure of ${victims
        .map((v) => `${v.label} (${v.sub}, ${v.severity})`)
        .join(", ")}`
    : "The new prescription does not use a cytochrome P450 pathway, so no enzyme competition was found";

  return (
    <svg viewBox="0 0 440 240" width="100%" role="img" aria-label={aria}>
      {/* Rx -> enzyme */}
      <line x1="110" y1="120" x2={CX - R} y2="120" stroke={rxStyle.color} strokeWidth={rxStyle.width + 0.5}
            strokeDasharray={none ? "5 4" : undefined} />
      {rxEdge && rxEdge.label !== "none" && (
        <text x="148" y="110" fontSize="11" fill={rxStyle.color} textAnchor="middle">{rxEdge.label}</text>
      )}

      {/* enzyme -> victims */}
      {victims.map((v, i) => {
        const e = edges.find((x) => x.to === v.id);
        const st = SEV[e?.severity || "none"];
        const ang = Math.atan2(ys[i] - CY, VX - CX);
        return (
          <line key={v.id} x1={CX + R * Math.cos(ang)} y1={CY + R * Math.sin(ang)} x2={VX} y2={ys[i]}
                stroke={st.color} strokeWidth={st.width} />
        );
      })}

      {/* Rx node */}
      <rect x="10" y="98" width="100" height="44" rx="8" fill="#1F4E8C" />
      <text x="60" y="117" fontSize="11" fill="#fff" textAnchor="middle">New Rx</text>
      <text x="60" y="132" fontSize="12" fontWeight="600" fill="#fff" textAnchor="middle">{nodes[0].sub}</text>

      {/* enzyme / no-pathway node */}
      {enzyme && (
        <>
          <circle cx={CX} cy={CY} r={R} fill={enzyme.saturated ? "#FEE4E2" : "#FEF3C7"} stroke={enzyme.saturated ? "#B42318" : "#B45309"} strokeWidth="2" />
          <text x={CX} y="118" fontSize="12" fontWeight="700" fill="#0F2137" textAnchor="middle">{enzyme.label}</text>
          <text x={CX} y="133" fontSize="11" fill={enzyme.saturated ? "#B42318" : "#92400E"} textAnchor="middle">{enzyme.sub}</text>
        </>
      )}
      {none && (
        <>
          <circle cx={CX} cy={CY} r={R} fill="#F4F7FB" stroke="#9AA9BC" strokeWidth="2" strokeDasharray="5 4" />
          <text x={CX} y="118" fontSize="12" fontWeight="600" fill="#0F2137" textAnchor="middle">No CYP</text>
          <text x={CX} y="133" fontSize="11" fill="#5B6B7F" textAnchor="middle">pathway</text>
        </>
      )}

      {/* victim nodes */}
      {victims.map((v, i) => {
        const e = edges.find((x) => x.to === v.id);
        const st = SEV[v.severity || "none"];
        return (
          <g key={v.id}>
            <rect x={VX} y={ys[i] - VH / 2} width={VW} height={VH} rx="8" fill="#fff" stroke={st.color} strokeWidth="2" />
            <text x={VX + VW / 2} y={ys[i] - 2} fontSize="12" fontWeight="600" fill="#0F2137" textAnchor="middle">{v.label}</text>
            <text x={VX + VW / 2} y={ys[i] + 12} fontSize="10" fill="#5B6B7F" textAnchor="middle">{v.sub}</text>
            <text x={VX + VW / 2} y={ys[i] + VH / 2 + 12} fontSize="10" fontWeight="600" fill={st.color} textAnchor="middle">{e?.label}</text>
          </g>
        );
      })}
    </svg>
  );
}
