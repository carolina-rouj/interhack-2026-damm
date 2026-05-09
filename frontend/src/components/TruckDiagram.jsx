// 18 distinct colors for clients
const PALETTE = [
  '#4e79a7','#f28e2b','#e15759','#76b7b2','#59a14f',
  '#edc948','#b07aa1','#ff9da7','#9c755f','#bab0ac',
  '#17becf','#aec7e8','#ffbb78','#98df8a','#ff9896',
  '#c5b0d5','#c49c94','#f7b6d2',
]

function getColor(clientId, clientColorMap) {
  return clientColorMap[clientId] || '#e5e7eb'
}

export default function TruckDiagram({ loadPlan, stops }) {
  if (!loadPlan) return null

  // Build color map: client_id -> color
  const clientColorMap = {}
  if (stops) {
    stops.forEach((stop, i) => {
      clientColorMap[stop.client.client_id] = PALETTE[i % PALETTE.length]
    })
  }

  // Build slot map: slot_id -> assignment
  const slotMap = {}
  loadPlan.assignments.forEach((a) => {
    const id = a.slot.slot_id
    if (!slotMap[id]) slotMap[id] = []
    slotMap[id].push(a)
  })

  // Legend
  const legendItems = stops
    ? stops.map((stop, i) => ({
        clientId: stop.client.client_id,
        name: stop.client.name,
        color: PALETTE[i % PALETTE.length],
        pos: i + 1,
      }))
    : []

  function renderCell(slotId) {
    const assignments = slotMap[slotId] || []
    const isRetorn = assignments.some((a) => a.is_returnable_buffer)

    if (isRetorn) {
      return (
        <div key={slotId} className="pallet-cell" style={{ background: '#f3f4f6', color: '#6b7280' }}>
          <span className="slot-num">P{slotId}</span>
          <div style={{ fontSize: 16 }}>📦</div>
          <div style={{ fontWeight: 700 }}>RETORN</div>
          <div className="boxes">reservado</div>
        </div>
      )
    }

    if (assignments.length === 0) {
      return (
        <div key={slotId} className="pallet-cell" style={{ background: '#f9fafb', color: '#9ca3af' }}>
          <span className="slot-num">P{slotId}</span>
          <div>vacío</div>
        </div>
      )
    }

    // Single client or split
    const primary = assignments[0]
    const color = getColor(primary.client_id, clientColorMap)
    const textColor = isLight(color) ? '#1a1a2e' : '#fff'
    const isSplit = assignments.length > 1 || assignments.some(a => a.boxes < 60 && !a.is_returnable_buffer)

    return (
      <div
        key={slotId}
        className="pallet-cell"
        style={{ background: color, color: textColor }}
        title={assignments.map(a => `${a.client_name}: ${a.boxes} cajas`).join(' | ')}
      >
        <span className="slot-num" style={{ opacity: .7 }}>P{slotId}</span>
        {primary.delivery_position > 0 && (
          <span className="delivery-pos">{primary.delivery_position}</span>
        )}
        <div style={{ fontWeight: 700, fontSize: 10, textAlign: 'center', lineHeight: 1.2 }}>
          {assignments.map(a => a.client_name?.split(' ').slice(-1)[0]).join(' / ')}
        </div>
        <div className="boxes">
          {assignments.map(a => `${a.boxes} cajas`).join(' + ')}
        </div>
        {isSplit && <div style={{ fontSize: 9, opacity: .7 }}>split</div>}
      </div>
    )
  }

  // Slot order: row 1 (rear) first — slots 1,2 then 3,4 then 5,6
  const slotOrder = [1, 2, 3, 4, 5, 6]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="truck-wrap">
        <div className="truck-label">🚪 Puerta trasera (descarga)</div>
        <div className="truck-with-sides">
          <div className="side-label left">← Lona lateral</div>
          <div className="truck-grid">
            {slotOrder.map(renderCell)}
          </div>
          <div className="side-label">Lona lateral →</div>
        </div>
        <div className="truck-label">🚗 Cabina conductor</div>
      </div>

      {loadPlan.warnings && loadPlan.warnings.length > 0 && (
        <div>
          <h3 style={{ fontSize: 13, marginBottom: 8 }}>Avisos de carga</h3>
          <div className="warn-list">
            {loadPlan.warnings.map((w, i) => (
              <div key={i} className={`warn-item ${w.startsWith('CONFLICTO') ? 'conflict' : ''}`}>
                {w}
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 style={{ fontSize: 13, marginBottom: 8 }}>Leyenda de clientes</h3>
        <div className="legend">
          {legendItems.map((item) => (
            <div key={item.clientId} className="legend-item">
              <div className="legend-dot" style={{ background: item.color }} />
              <span>{item.pos}. {item.name}</span>
            </div>
          ))}
          <div className="legend-item">
            <div className="legend-dot" style={{ background: '#f3f4f6', border: '1px solid #d1d5db' }} />
            <span>Retornables</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function isLight(hex) {
  const c = hex.replace('#', '')
  const r = parseInt(c.substr(0, 2), 16)
  const g = parseInt(c.substr(2, 2), 16)
  const b = parseInt(c.substr(4, 2), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 > 160
}
