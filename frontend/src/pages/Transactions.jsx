import { useEffect, useState } from "react";
import TransactionTable from "../components/TransactionTable";
import RiskBadge from "../components/RiskBadge";
import { api } from "../services/api";

const initialForm = { source_account_id: "", destination_account_id: "", amount: "", description: "" };

export default function Transactions() {
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try { setTransactions(await api.getTransactions()); } catch (err) { setError(err.message); }
  }
  useEffect(() => { api.getAccounts().then(setAccounts).catch((err) => setError(err.message)); refresh(); }, []);
  function update(field, value) { setForm((current) => ({ ...current, [field]: value })); }
  async function submit(event) {
    event.preventDefault();
    setBusy(true); setError(""); setResult(null);
    try {
      const response = await api.createTransfer({
        source_account_id: Number(form.source_account_id),
        destination_account_id: Number(form.destination_account_id),
        amount: form.amount,
        description: form.description || null,
      });
      setResult(response); setForm(initialForm); await refresh();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return (
    <div className="page-stack">
      <div className="section-heading"><div><p className="eyebrow">MONEY MOVEMENT</p><h2>Transactions</h2></div><button className="button ghost" onClick={refresh}>Refresh</button></div>
      {error && <div className="error-banner">{error}</div>}
      <section className="content-card">
        <div className="section-heading compact"><div><p className="eyebrow">SIMULATE</p><h3>New transfer</h3></div></div>
        <form className="transfer-form" onSubmit={submit}>
          <label>Source account<select required value={form.source_account_id} onChange={(event) => update("source_account_id", event.target.value)}><option value="">Choose account</option>{accounts.map((account) => <option key={account.account_id} value={account.account_id}>{account.account_number} · {account.balance} {account.currency_code}</option>)}</select></label>
          <label>Destination account<select required value={form.destination_account_id} onChange={(event) => update("destination_account_id", event.target.value)}><option value="">Choose account</option>{accounts.map((account) => <option key={account.account_id} value={account.account_id}>{account.account_number}</option>)}</select></label>
          <label>Amount<input required min="0.01" step="0.0001" type="number" value={form.amount} onChange={(event) => update("amount", event.target.value)} /></label>
          <label>Description<input maxLength="500" value={form.description} onChange={(event) => update("description", event.target.value)} /></label>
          <button className="button primary" disabled={busy}>{busy ? "Evaluating…" : "Submit transfer"}</button>
        </form>
        {result && <div className="result-banner"><div><strong>Transfer #{result.transaction.transaction_id} {result.transaction.status}</strong><p className="muted">The C++ rules engine evaluated this request before PostgreSQL processing.</p></div><RiskBadge level={result.risk_level} /><span className="score">Score {Number(result.combined_risk_score).toFixed(3)}</span></div>}
      </section>
      <section className="content-card"><div className="section-heading compact"><div><p className="eyebrow">HISTORY</p><h3>Recent transactions</h3></div></div><TransactionTable transactions={transactions} /></section>
    </div>
  );
}
