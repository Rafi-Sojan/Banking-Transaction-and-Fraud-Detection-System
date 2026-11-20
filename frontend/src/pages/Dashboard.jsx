import { useEffect, useState } from "react";
import FraudAlert from "../components/FraudAlert";
import TransactionTable from "../components/TransactionTable";
import { api } from "../services/api";

export default function Dashboard({ user }) {
  const [data, setData] = useState({ accounts: [], transactions: [], alerts: [] });
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api.getAccounts(), api.getTransactions(), api.getAlerts()])
      .then(([accounts, transactions, alerts]) => setData({ accounts, transactions, alerts }))
      .catch((err) => setError(err.message));
  }, []);
  const openAlerts = data.alerts.filter((alert) => alert.alert_status !== "resolved" && alert.alert_status !== "dismissed");
  return (
    <div className="page-stack">
      <section className="hero-card">
        <div><p className="eyebrow">WELCOME BACK</p><h2>{user.username}</h2><p className="muted">Your latest ledger activity and fraud signals in one place.</p></div>
        <div className="hero-mark">{String(user.role_name || "").slice(0, 2).toUpperCase()}</div>
      </section>
      {error && <div className="error-banner">{error}</div>}
      <section className="stat-grid">
        <div className="stat-card"><span>Accounts</span><strong>{data.accounts.length}</strong><small>Visible to your role</small></div>
        <div className="stat-card"><span>Transactions</span><strong>{data.transactions.length}</strong><small>Most recent records</small></div>
        <div className="stat-card"><span>Open alerts</span><strong>{openAlerts.length}</strong><small>Needs attention</small></div>
      </section>
      <section className="content-card"><div className="section-heading"><div><p className="eyebrow">LEDGER</p><h2>Recent transactions</h2></div></div><TransactionTable transactions={data.transactions.slice(0, 8)} /></section>
      {openAlerts.length > 0 && <section><div className="section-heading"><div><p className="eyebrow">RISK QUEUE</p><h2>Open fraud alerts</h2></div></div><div className="alert-grid-list">{openAlerts.slice(0, 3).map((alert) => <FraudAlert key={alert.alert_id} alert={alert} canInvestigate={false} />)}</div></section>}
    </div>
  );
}
