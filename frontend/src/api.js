const BASE = '/api'

export async function generateScenario(seed = 42, nClients = 16) {
  const res = await fetch(`${BASE}/scenario/generate?seed=${seed}&n_clients=${nClients}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function optimizeScenario(scenarioId, startTime = '08:00') {
  const res = await fetch(`${BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId, start_time: startTime }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
