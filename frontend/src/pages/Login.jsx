import { useState } from "react";
import { login } from "../services/api";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(await login(username, password));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand-mark large">BF</div>
        <p className="eyebrow">SIMULATION CONSOLE</p>
        <h1>Sign in to fraud operations</h1>
        <p className="muted">Review synthetic transactions, alerts, and investigations through the FastAPI backend.</p>
        <form onSubmit={submit} className="stack-form">
          <label>Username<input required value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label>
          <label>Password<input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>
          {error && <div className="error-banner">{error}</div>}
          <button className="button primary full-width" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        </form>
      </section>
    </main>
  );
}
