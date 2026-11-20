import { useEffect, useState } from "react";
import { api } from "../services/api";

export default function Investigations() {
  const [investigations, setInvestigations] = useState([]);
  const [notes, setNotes] = useState({});
  const [error, setError] = useState("");
  async function refresh() { try { setInvestigations(await api.getInvestigations()); } catch (err) { setError(err.message); } }
  useEffect(() => { refresh(); }, []);
  async function addAction(id) { try { await api.addInvestigationAction(id, { action_type: "reviewed", notes: notes[id] || "Review recorded from console." }); setNotes((current) => ({ ...current, [id]: "" })); await refresh(); } catch (err) { setError(err.message); } }
  async function close(id, outcome) { try { await api.closeInvestigation(id, { outcome, notes: notes[id] || null }); await refresh(); } catch (err) { setError(err.message); } }
  return <div className="page-stack"><div className="section-heading"><div><p className="eyebrow">CASE MANAGEMENT</p><h2>Investigations</h2></div><button className="button ghost" onClick={refresh}>Refresh</button></div>{error && <div className="error-banner">{error}</div>}<div className="case-list">{investigations.map((item) => <article className="content-card case-card" key={item.investigation_id}><div className="section-heading compact"><div><p className="eyebrow">CASE #{item.investigation_id}</p><h3>Alert #{item.alert_id}</h3></div><span className={`status status-${item.investigation_status}`}>{item.investigation_status}</span></div><p>{item.notes || "No opening notes."}</p><textarea placeholder="Add investigator notes" value={notes[item.investigation_id] || ""} onChange={(event) => setNotes((current) => ({ ...current, [item.investigation_id]: event.target.value }))} /><div className="card-actions"><button className="button ghost" onClick={() => addAction(item.investigation_id)}>Add review action</button>{item.investigation_status !== "closed" && <><button className="button success" onClick={() => close(item.investigation_id, "legitimate")}>Close legitimate</button><button className="button danger" onClick={() => close(item.investigation_id, "confirmed_fraud")}>Confirm fraud</button></>}</div></article>)}</div>{!investigations.length && !error && <div className="empty-state">No investigations found.</div>}</div>;
}
