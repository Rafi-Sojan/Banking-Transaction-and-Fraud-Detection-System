import RiskBadge from "./RiskBadge";

function money(value, currency = "USD") {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(Number(value || 0));
}

export default function TransactionTable({ transactions, emptyText = "No transactions found." }) {
  if (!transactions.length) return <div className="empty-state">{emptyText}</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>ID</th><th>Amount</th><th>Type</th><th>Status</th><th>Time</th><th>Risk</th></tr>
        </thead>
        <tbody>
          {transactions.map((transaction) => (
            <tr key={transaction.transaction_id}>
              <td className="mono">#{transaction.transaction_id}</td>
              <td>{money(transaction.amount, transaction.currency_code)}</td>
              <td>{transaction.transaction_type}</td>
              <td><span className={`status status-${transaction.status}`}>{transaction.status}</span></td>
              <td>{new Date(transaction.transaction_timestamp).toLocaleString()}</td>
              <td>{transaction.risk_level ? <RiskBadge level={transaction.risk_level} /> : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
