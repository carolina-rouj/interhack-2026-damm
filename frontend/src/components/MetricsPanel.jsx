export default function MetricsPanel({ metrics }) {
  if (!metrics) return null

  const cards = [
    { label: 'Distancia total', value: metrics.total_distance_km, unit: 'km' },
    { label: 'Tiempo de ruta', value: `${Math.floor(metrics.total_time_min / 60)}h ${metrics.total_time_min % 60}m`, unit: '' },
    { label: 'Utilización camión', value: `${metrics.truck_utilization_pct}%`, unit: '' },
    { label: 'CO₂ estimado', value: metrics.co2_kg, unit: 'kg' },
    { label: 'Paradas', value: metrics.stops_total, unit: '' },
    { label: 'Incumpl. horarios', value: metrics.time_window_violations, unit: '' },
    { label: 'Prioritarios servidos', value: metrics.priority1_served, unit: '' },
    { label: 'Palés retornables', value: metrics.returnables_pallets_reserved, unit: 'reservados' },
  ]

  return (
    <div className="metrics-grid">
      {cards.map((c) => (
        <div key={c.label} className="metric-card">
          <span className="label">{c.label}</span>
          <span className="value">{c.value}</span>
          {c.unit && <span className="unit">{c.unit}</span>}
        </div>
      ))}
    </div>
  )
}
