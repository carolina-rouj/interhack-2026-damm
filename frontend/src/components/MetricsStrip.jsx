import { Van, Truck } from 'lucide-react';

const TRUCK_ICONS = { furgoneta: Van, mediano: Truck, grande: Truck };

function TrucksValue({ trucks = {} }) {
  const entries = Object.entries(trucks);
  if (!entries.length) return <span>—</span>;
  return (
    <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
      {entries.map(([t, n]) => {
        const Icon = TRUCK_ICONS[t] ?? Truck;
        return (
          <span key={t} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Icon size={22} strokeWidth={1.5} />
            <span style={{ fontSize: '16px', fontWeight: 700 }}>×{n}</span>
          </span>
        );
      })}
    </span>
  );
}

export default function MetricsStrip({ metrics }) {
  const cards = [
    { value: metrics.num_rutas,                             label: 'Routes' },
    { value: <TrucksValue trucks={metrics.trucks} />,       label: 'Trucks' },
    { value: metrics.total_palets,                          label: 'Pallets' },
    { value: (metrics.coste_total ?? 0).toFixed(2),         label: 'Est. Cost' },
    { value: metrics.total_cajas_entregadas,                label: 'Boxes Delivered' },
  ];

  return (
    <div className="metrics-strip">
      {cards.map(c => (
        <div key={c.label} className="metric-card">
          <div className="metric-value">{c.value}</div>
          <div className="metric-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
