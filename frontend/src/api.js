const BASE = '';

export const listZones = () =>
  fetch(`${BASE}/api/zona/list`).then(r => r.json());

export const solve = (zonaId, cajasPorPalet) =>
  fetch(`${BASE}/api/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zona_id: zonaId, cajas_por_palet: cajasPorPalet }),
  }).then(r => {
    if (!r.ok) throw new Error(`Server error ${r.status}`);
    return r.json();
  });
