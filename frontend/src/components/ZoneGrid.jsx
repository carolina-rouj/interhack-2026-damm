import ZoneCard from './ZoneCard.jsx';

export default function ZoneGrid({ zones, selected, onSelect }) {
  if (!zones.length) {
    return <p style={{ color: 'var(--muted)', marginBottom: '32px' }}>Loading zones…</p>;
  }
  return (
    <div className="zone-grid">
      {zones.map(id => (
        <ZoneCard
          key={id}
          id={id}
          selected={selected === id}
          onClick={() => onSelect(id)}
        />
      ))}
    </div>
  );
}
