// Android emulator → host machine loopback. Change to LAN IP for physical device:
// e.g. 'http://192.168.1.X:8000'
export const BASE_URL = 'http://10.0.2.2:8000'

export async function generateScenario(seed = 42, nClients = 16) {
  const res = await fetch(`${BASE_URL}/api/scenario/generate?seed=${seed}&n_clients=${nClients}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function optimizeScenario(scenarioId, startTime = '08:00') {
  const res = await fetch(`${BASE_URL}/api/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      zona_id: zonaId,
      cajas_por_palet: cajasPorPalet,
      distancia_max: distanciaMax,
      usar_google: usarGoogle,
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
