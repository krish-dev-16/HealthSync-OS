import { useEffect, useRef } from "react";

export default function AgentTrace({ trace }) {
  const box = useRef(null);
  const prevLen = useRef(trace.length);

  // When new entries arrive (for example after approval), scroll so they are visible.
  useEffect(() => {
    if (trace.length > prevLen.current && box.current) {
      box.current.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" });
    }
    prevLen.current = trace.length;
  }, [trace.length]);

  return (
    <div className="trace" ref={box} tabIndex={0} role="region" aria-label="Agent trace">
      {trace.map((t, i) => (
        <div key={i}>
          <b>{t.agent}</b> · {t.action}
          {t.detail && <div className="detail">{t.detail}</div>}
          {t.source && <div className="detail src">Source: {t.source}</div>}
        </div>
      ))}
    </div>
  );
}
