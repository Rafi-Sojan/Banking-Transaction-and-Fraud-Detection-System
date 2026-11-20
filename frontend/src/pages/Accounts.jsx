import { useEffect, useState } from "react";
import { api } from "../services/api";

export default function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => { api.getAccounts().then(setAccounts).catch((err) => setError(err.message)); }, []);
  return <div className="page-stack"><div className="section-heading"><div><p className="eyebrow">LEDGER</p><h2>Accounts</h2></div></div>{error && <div className="error-banner">{error}</div>}<div className="card-grid">{accounts.map((account) => <article className="content-card account-card" key={account.account_id}><span className="eyebrow">{account.account_type}</span><h3>{account.account_number}</h3><strong>{account.currency_code} {account.balance}</strong><p className="muted">{account.status} · account #{account.account_id}</p></article>)}</div>{!accounts.length && !error && <div className="empty-state">No accounts found.</div>}</div>;
}
