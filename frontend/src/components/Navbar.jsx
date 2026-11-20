export default function Navbar({ user, onLogout }) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">CONTROL ROOM</p>
        <h1>Banking fraud operations</h1>
      </div>
      <div className="user-menu">
        <span>{user.username}</span>
        <span className="role-pill">{user.role_name}</span>
        <button className="button ghost" onClick={onLogout}>Sign out</button>
      </div>
    </header>
  );
}
