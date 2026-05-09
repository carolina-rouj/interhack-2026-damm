function fmtMin(m) {
  return `${Math.floor(m / 60).toString().padStart(2, '0')}:${(m % 60).toString().padStart(2, '0')}`
}

export default function ClientTable({ stops, orders }) {
  if (!stops || stops.length === 0) return <p style={{ color: 'var(--muted)', fontSize: 13 }}>Sin datos de ruta.</p>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Cliente</th>
            <th>Ventana horaria</th>
            <th>Llegada</th>
            <th>Espera</th>
            <th>Prio</th>
            <th>Cajas</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {stops.map((stop, i) => {
            const order = orders?.[stop.client.client_id]
            const tw = stop.client.time_window
            const isViolated = stop.status === 'TIME_WINDOW_VIOLATED'
            return (
              <tr key={stop.client.client_id}>
                <td style={{ fontWeight: 700 }}>{i + 1}</td>
                <td>
                  <div style={{ fontWeight: 600 }}>{stop.client.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>{stop.client.restriction !== 'none' ? `⚠ ${stop.client.restriction}` : ''}</div>
                </td>
                <td style={{ fontFamily: 'monospace' }}>{fmtMin(tw.open_min)} – {fmtMin(tw.close_min)}</td>
                <td style={{ fontFamily: 'monospace' }}>{stop.arrival_time}</td>
                <td>{stop.wait_min > 0 ? <span className="badge badge-yellow">{stop.wait_min} min</span> : <span style={{ color: 'var(--muted)' }}>—</span>}</td>
                <td>
                  <span className={`prio prio-${stop.client.priority}`} title={`Prioridad ${stop.client.priority}`} />
                </td>
                <td>{order ? order.total_boxes : '—'}</td>
                <td>
                  {isViolated
                    ? <span className="badge badge-red">Incumplido</span>
                    : stop.wait_min > 0
                    ? <span className="badge badge-yellow">A tiempo (espera)</span>
                    : <span className="badge badge-green">OK</span>}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
