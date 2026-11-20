import { useEffect, useState } from "react";
import { api } from "../services/api";

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => { api.getCustomers().then(setCustomers).catch((err) => setError(err.message)); }, []);
  return <div className="page-stack"><div className="section-heading"><div><p className="eyebrow">IDENTITY</p><h2>Customers</h2></div></div>{error && <div className="error-banner">{error}</div>}<div className="card-grid">{customers.map((customer) => <article className="content-card" key={customer.customer_id}><h3>{customer.full_name}</h3><p>{customer.email}</p><p className="muted">{customer.status} · customer #{customer.customer_id}</p></article>)}</div>{!customers.length && !error && <div className="empty-state">No customers found.</div>}</div>;
}
