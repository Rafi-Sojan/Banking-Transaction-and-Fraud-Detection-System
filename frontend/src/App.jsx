import { useState } from "react";
import { clearSession, getSession } from "./services/api";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import FraudAlerts from "./pages/FraudAlerts";
import Investigations from "./pages/Investigations";
import Accounts from "./pages/Accounts";
import Customers from "./pages/Customers";

export default function App() {
  const [session, setSession] = useState(getSession);
  const [view, setView] = useState("dashboard");

  if (!session?.access_token || !session?.user) {
    return <Login onLogin={(nextSession) => setSession(nextSession)} />;
  }

  const logout = () => {
    clearSession();
    setSession(null);
  };
  const role = session.user.role_name;
  const page = {
    dashboard: <Dashboard user={session.user} />,
    transactions: <Transactions user={session.user} />,
    alerts: <FraudAlerts user={session.user} />,
    investigations: <Investigations user={session.user} />,
    accounts: <Accounts />,
    customers: <Customers />,
  }[view] || <Dashboard user={session.user} />;

  return (
    <div className="app-shell">
      <Sidebar activeView={view} onNavigate={setView} role={role} />
      <div className="app-main">
        <Navbar user={session.user} onLogout={logout} />
        <main className="page-content">{page}</main>
      </div>
    </div>
  );
}
