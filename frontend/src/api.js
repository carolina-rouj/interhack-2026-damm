const BASE = '/api'

export async function listZonas() {
  const res = await fetch(`${BASE}/zona/list`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function loadZona(zonaId) {
  const res = await fetch(`${BASE}/zona/${encodeURIComponent(zonaId)}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function clusterZona(zonaId, { cajasPorPalet = 60, distanciaMax = null, usarGoogle = false } = {}) {
  const res = await fetch(`${BASE}/cluster`, {
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
