import { useState } from 'react'
import { generateScenario, optimizeScenario } from './api.js'
import MetricsPanel from './components/MetricsPanel.jsx'
import ClientTable from './components/ClientTable.jsx'
import TruckDiagram from './components/TruckDiagram.jsx'
import RouteMap from './components/RouteMap.jsx'

export default function App() {
  const [seed, setSeed] = useState(42)
  const [nClients, setNClients] = useState(16)
  const [startTime, setStartTime] = useState('08:00')

  const [scenario, setScenario] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('route')

  async function handleGenerate() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await generateScenario(seed, nClients)
      setScenario(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleOptimize() {
    if (!scenario) return
    setLoading(true)
    setError(null)
    try {
      const data = await optimizeScenario(scenario.scenario_id, startTime)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const stops = result?.route?.stops || []
  const orders = scenario?.orders || {}

  return (
    <div className="app">
      <nav className="navbar">
        <h1><span>DAMM</span> Smart Truck</h1>
        <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 'auto' }}>Interhack BCN 2026</span>
      </nav>

      <div className="layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <h2>Configuración</h2>

          <div className="form-row">
            <label>Semilla aleatoria</label>
            <input type="number" value={seed} min={1} max={9999}
              onChange={e => setSeed(Number(e.target.value))} />
          </div>

          <div className="form-row">
            <label>Número de clientes</label>
            <input type="number" value={nClients} min={5} max={20}
              onChange={e => setNClients(Number(e.target.value))} />
          </div>

          <div className="form-row">
            <label>Hora inicio ruta</label>
            <input type="time" value={startTime}
              onChange={e => setStartTime(e.target.value)} />
          </div>

          <button className="btn btn-secondary" onClick={handleGenerate} disabled={loading}>
            {loading ? '⏳ Cargando...' : '🎲 Generar escenario'}
          </button>

          {scenario && (
            <button className="btn btn-primary" onClick={handleOptimize} disabled={loading}>
              {loading ? '⏳ Optimizando...' : '⚡ Optimizar ruta + carga'}
            </button>
          )}

          {scenario && (
            <div className="card" style={{ fontSize: 12 }}>
              <h3 style={{ marginBottom: 8 }}>Escenario activo</h3>
              <div><strong>Zona:</strong> {scenario.zone.name}</div>
              <div><strong>Depósito:</strong> {scenario.zone.depot.name}</div>
              <div><strong>Clientes:</strong> {scenario.clients.length}</div>
              <div><strong>Pedidos:</strong> {Object.keys(scenario.orders).length}</div>
            </div>
          )}

          {error && (
            <div className="warn-item conflict" style={{ fontSize: 12 }}>
              ❌ {error}
            </div>
          )}
        </aside>

        {/* Main content */}
        <main className="content">
          {!scenario && !loading && (
            <div className="empty-state">
              <div style={{ fontSize: 48 }}>🚛</div>
              <h2>Damm Smart Truck</h2>
              <p>Genera un escenario y optimiza la ruta y la carga del camión.</p>
            </div>
          )}

          {loading && <div className="spinner" />}

          {result && !loading && (
            <>
              <MetricsPanel metrics={result.metrics} />

              <div className="tabs">
                {[
                  { key: 'route', label: '🗺 Ruta' },
                  { key: 'load', label: '📦 Carga del camión' },
                  { key: 'explain', label: '💡 Explicaciones' },
                ].map(t => (
                  <button key={t.key} className={`tab ${tab === t.key ? 'active' : ''}`}
                    onClick={() => setTab(t.key)}>
                    {t.label}
                  </button>
                ))}
              </div>

              {tab === 'route' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <RouteMap stops={stops} depot={scenario?.zone?.depot} />
                  <div className="card">
                    <h3>Tabla de paradas</h3>
                    <ClientTable stops={stops} orders={orders} />
                  </div>
                  <ReturnablesSummary returnablesPlan={result.returnables_plan} stops={stops} />
                </div>
              )}

              {tab === 'load' && (
                <div className="two-col">
                  <div className="card">
                    <h3>Distribución de palés</h3>
                    <TruckDiagram loadPlan={result.load_plan} stops={stops} />
                  </div>
                  <div className="card">
                    <h3>Detalle de asignación</h3>
                    <LoadTable loadPlan={result.load_plan} />
                  </div>
                </div>
              )}

              {tab === 'explain' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div className="card">
                    <h3>Justificación de la ruta</h3>
                    <ul className="explain-list">
                      {result.route.explanations.map((e, i) => (
                        <li key={i} className={e.includes('AVISO') ? 'violated' : 'ok'}>{e}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="card">
                    <h3>Criterios de optimización</h3>
                    <OptCriteria metrics={result.metrics} />
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  )
}

function ReturnablesSummary({ returnablesPlan, stops }) {
  if (!returnablesPlan || returnablesPlan.total_expected_boxes === 0) return null
  return (
    <div className="card">
      <h3>Logística inversa — Retornables</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8, marginBottom: 12 }}>
        <div><strong>{returnablesPlan.total_expected_boxes}</strong> cajas esperadas</div>
        <div><strong>{returnablesPlan.pallets_reserved}</strong> palé(s) reservado(s)</div>
        <div>Slots: P{returnablesPlan.reserved_slot_ids.join(', P')}</div>
      </div>
      <table>
        <thead>
          <tr><th>Cliente</th><th>Retornables esperados (cajas)</th></tr>
        </thead>
        <tbody>
          {stops.filter(s => returnablesPlan.per_client[s.client.client_id]).map(s => (
            <tr key={s.client.client_id}>
              <td>{s.client.name}</td>
              <td>{returnablesPlan.per_client[s.client.client_id]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function LoadTable({ loadPlan }) {
  if (!loadPlan) return null
  const sorted = [...loadPlan.assignments].sort((a, b) => a.slot.slot_id - b.slot.slot_id)
  return (
    <div style={{ overflowX: 'auto' }}>
      <table>
        <thead>
          <tr>
            <th>Palé</th>
            <th>Fila</th>
            <th>Acceso</th>
            <th>Cliente</th>
            <th>Cajas</th>
            <th>Posición entrega</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((a, i) => (
            <tr key={i}>
              <td><strong>P{a.slot.slot_id}</strong></td>
              <td>{a.slot.row === 1 ? 'Trasera' : a.slot.row === 2 ? 'Central' : 'Delantera'}</td>
              <td style={{ fontSize: 11 }}>{a.slot.accessible_from.join(', ')}</td>
              <td>
                {a.is_returnable_buffer
                  ? <span className="badge badge-gray">📦 Retornables</span>
                  : a.client_name}
              </td>
              <td>{a.boxes || '—'}</td>
              <td>
                {a.is_returnable_buffer ? '—' : <span className="badge badge-blue">#{a.delivery_position}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OptCriteria({ metrics }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
      <p><strong>Algoritmo de ruta:</strong> Heurística Vecino Más Cercano + mejora 2-opt con respeto de ventanas horarias. Se penaliza la distancia multiplicada por el peso de prioridad del cliente (clientes prioritarios tienen peso 0.5×, normales 1.5×).</p>
      <p><strong>Velocidades de tráfico aplicadas:</strong> 15 km/h (rush 7-9h), 25 km/h (9-13h), 20 km/h (13-15h), 30 km/h (resto).</p>
      <p><strong>Carga del camión:</strong> Asignación LIFO — primeros en entregar = palés traseros (P1/P2, acceso puerta). La lona lateral permite acceso a palés centrales y delanteros.</p>
      <p><strong>Retornables:</strong> Se reservan palés delanteros (P5/P6) para recoger envases vacíos durante la ruta, ya que se liberan al final del reparto.</p>
      <p><strong>CO₂ estimado:</strong> {metrics.co2_kg} kg (factor 0.27 kg/km para camión diésel). Total distancia: {metrics.total_distance_km} km.</p>
    </div>
  )
}
