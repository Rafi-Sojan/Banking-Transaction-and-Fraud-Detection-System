const commonLinks = [
  ["dashboard", "Overview"],
  ["transactions", "Transactions"],
  ["alerts", "Fraud alerts"],
  ["accounts", "Accounts"],
];

export default function Sidebar({ activeView, onNavigate, role }) {
  const links = role === "customer"
    ? commonLinks
    : [...commonLinks, ["investigations", "Investigations"], ["customers", "Customers"]];
  return (
    <aside className="sidebar">
      <div className="brand-mark">BF</div>
      <div className="brand-copy">
        <strong>Banking Fraud</strong>
        <span>Simulation console</span>
      </div>
      <nav className="side-nav" aria-label="Primary navigation">
        {links.map(([id, label]) => (
          <button
            className={`nav-item ${activeView === id ? "active" : ""}`}
            key={id}
            onClick={() => onNavigate(id)}
          >
            {label}
          </button>
        ))}
      </nav>
      <p className="sidebar-note">Synthetic data only. PostgreSQL remains the authoritative ledger.</p>
    </aside>
  );
}
