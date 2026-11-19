export default function Pill({ tone = "idle", children }) {
  return <span className={`pill pill--${tone}`}>{children}</span>;
}
