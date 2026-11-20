import { useEffect, useState } from "react";
import FraudAlert from "../components/FraudAlert";
import { api } from "../services/api";

export default function FraudAlerts({ user }) {
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");
  const canInvestigate = ["investigator", "administrator"].includes(user.role_name);
  async function refresh() { try { setAlerts(await api.getAlerts()); } catch (err) { setError(err.message); } }
  useEffect(() => { refresh(); }, []);
  async function openInvestigation(alertId) { try { await api.openInvestigation(alertId, {}); await refresh(); } catch (err) { setError(err.message); } }
  async function updateStatus(alertId, status) { try { await api.updateAlertStatus(alertId, status); await refresh(); } catch (err) { setError(err.message); } }
  return <div className="page-stack"><div className="section-heading"><div><p className="eyebrow">RISK QUEUE</p><h2>Fraud alerts</h2><p className="muted">Rule evidence and model scores remain separate from final investigation outcomes.</p></div><button className="button ghost" onClick={refresh}>Refresh</button></div>{error && <div className="error-banner">{error}</div>}<div className="alert-grid-list">{alerts.map((alert) => <FraudAlert key={alert.alert_id} alert={alert} canInvestigate={canInvestigate} onOpenInvestigation={openInvestigation} onStatusChange={updateStatus} />)}</div>{!alerts.length && !error && <div className="empty-state">No fraud alerts found.</div>}</div>;
}
