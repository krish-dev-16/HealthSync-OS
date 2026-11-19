export default function PAStepper({ steps }) {
  return (
    <ol className="steps">
      {steps.map((s) => (
        <li key={s.label} className={s.state}>
          <span className={`dot dot--${s.state}`} aria-hidden="true" />
          {s.label}
        </li>
      ))}
    </ol>
  );
}
