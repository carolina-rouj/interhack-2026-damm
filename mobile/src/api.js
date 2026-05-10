// Change to your machine's LAN IP when testing on a physical device
export const BASE_URL = 'http://10.128.174.178:8000'

export async function getZones() {
  const res = await fetch(`${BASE_URL}/api/zona/list`)
  if (!res.ok) throw new Error(await res.text())
  return res.json() // { zonas: string[] }
}

export async function solveRoute(zonaId, { cajasPorPalet = 60 } = {}) {
  const res = await fetch(`${BASE_URL}/api/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zona_id: zonaId, cajas_por_palet: cajasPorPalet, usar_google: false }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() // { zona_id, num_rutas, metrics, routes: [{file, route}] }
}
