export default function RiskBadge({ level }) {
  return <span className={`risk-badge risk-${String(level || "unknown").toLowerCase()}`}>{level || "unknown"}</span>;
}
