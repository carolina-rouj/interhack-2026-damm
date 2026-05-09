import { MapContainer, TileLayer, Marker, Polyline, Tooltip, CircleMarker } from 'react-leaflet'
import L from 'leaflet'

// Fix default Leaflet icon issue with Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const PRIORITY_COLORS = { 1: '#e10600', 2: '#f59e0b', 3: '#16a34a' }

function fmtMin(m) {
  return `${Math.floor(m / 60).toString().padStart(2, '0')}:${(m % 60).toString().padStart(2, '0')}`
}

export default function RouteMap({ stops, depot }) {
  if (!stops || stops.length === 0 || !depot) {
    return <div className="map-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f3f4f6', color: 'var(--muted)' }}>Sin datos de ruta</div>
  }

  const center = [depot.lat, depot.lon]
  const positions = [center, ...stops.map(s => [s.client.lat, s.client.lon]), center]

  return (
    <div className="map-container">
      <MapContainer center={center} zoom={14} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Route line */}
        <Polyline positions={positions} color="#1a1a2e" weight={2.5} opacity={0.6} dashArray="6 4" />

        {/* Depot marker */}
        <Marker position={center}>
          <Tooltip permanent direction="top" offset={[0, -10]}>
            <strong>🏭 Fábrica Damm</strong>
          </Tooltip>
        </Marker>

        {/* Client markers */}
        {stops.map((stop, i) => {
          const color = PRIORITY_COLORS[stop.client.priority] || '#6b7280'
          const isViolated = stop.status === 'TIME_WINDOW_VIOLATED'
          const tw = stop.client.time_window
          return (
            <CircleMarker
              key={stop.client.client_id}
              center={[stop.client.lat, stop.client.lon]}
              radius={14}
              pathOptions={{
                color: isViolated ? '#b91c1c' : color,
                fillColor: isViolated ? '#fca5a5' : color,
                fillOpacity: 0.9,
                weight: isViolated ? 3 : 1.5,
              }}
            >
              <Tooltip permanent direction="top" offset={[0, -12]}>
                <strong>{i + 1}</strong>
              </Tooltip>
              <Tooltip direction="right" offset={[16, 0]}>
                <div style={{ fontSize: 12, lineHeight: 1.5 }}>
                  <strong>{i + 1}. {stop.client.name}</strong><br />
                  Llegada: {stop.arrival_time}<br />
                  Ventana: {fmtMin(tw.open_min)}–{fmtMin(tw.close_min)}<br />
                  {stop.wait_min > 0 && <>Espera: {stop.wait_min} min<br /></>}
                  {isViolated && <span style={{ color: '#b91c1c' }}>⚠ Horario incumplido</span>}
                  {stop.client.expected_returnables > 0 && <>📦 Retornables: {stop.client.expected_returnables} cajas</>}
                </div>
              </Tooltip>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}
