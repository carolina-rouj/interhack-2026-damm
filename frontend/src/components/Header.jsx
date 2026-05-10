export default function Header() {
  return (
    <header className="site-header">
      <div className="header-inner">
        <img src="/logo.png" alt="Damm Smart Truck" className="header-logo" />
        <div className="header-text">
          <h1>Smart Truck</h1>
          <p>AI-powered delivery route optimization &mdash; Granollers</p>
        </div>
        <div className="header-badge">Interhack BCN 2026</div>
      </div>
    </header>
  );
}
