import RiskBadge from "./RiskBadge";

export default function FraudAlert({ alert, canInvestigate, onOpenInvestigation, onStatusChange }) {
  return (
    <article className="alert-card">
      <div className="alert-card-head">
        <div>
          <p className="eyebrow">ALERT #{alert.alert_id}</p>
          <h3>Transaction #{alert.transaction_id}</h3>
        </div>
        <RiskBadge level={alert.risk_level} />
      </div>
      <div className="alert-grid">
        <span><small>Amount</small><strong>{alert.currency_code} {alert.amount}</strong></span>
        <span><small>Score</small><strong>{Number(alert.combined_risk_score).toFixed(3)}</strong></span>
        <span><small>Status</small><strong>{alert.alert_status}</strong></span>
        <span><small>Type</small><strong>{alert.transaction_type}</strong></span>
      </div>
      <ul className="reason-list">
        {(alert.reasons || []).map((reason, index) => <li key={index}>{typeof reason === "string" ? reason : reason.reason || JSON.stringify(reason)}</li>)}
      </ul>
      <div className="card-actions">
        {canInvestigate && !alert.investigation_id && (
          <button className="button primary" onClick={() => onOpenInvestigation(alert.alert_id)}>Open investigation</button>
        )}
        {canInvestigate && (
          <select value={alert.alert_status} onChange={(event) => onStatusChange(alert.alert_id, event.target.value)}>
            <option value="open">Open</option>
            <option value="under_review">Under review</option>
            <option value="dismissed">Dismissed</option>
            <option value="resolved">Resolved</option>
          </select>
        )}
      </div>
    </article>
  );
}
