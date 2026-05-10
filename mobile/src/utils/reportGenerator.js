import * as Print from 'expo-print'
import * as Sharing from 'expo-sharing'

const TRUCK_LABELS = { '3pal': 'Furgoneta', '6pal': 'Camión mediano', '8pal': 'Camión grande' }

function formatDate(date) {
  return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function buildReportData(result) {
  const stops = result.route?.stops ?? []
  const routeId = result.route?.route_id
  const zonaId = result.route?.zona_id
  const truckLabel = TRUCK_LABELS[result.load_plan?.truck_type] ?? 'Camión'
  const today = formatDate(new Date())

  const skuMap = {}
  let grandCajas = 0
  let grandBarriles = 0
  stops.forEach(stop => {
    (stop.client.productos ?? []).forEach(p => {
      if (!skuMap[p.sku]) skuMap[p.sku] = { nombre: p.nombre, tipo_envase: p.tipo_envase, total: 0 }
      skuMap[p.sku].total += p.cantidad_cajas
      if (p.tipo_envase === 'barril') grandBarriles += p.cantidad_cajas
      else grandCajas += p.cantidad_cajas
    })
  })

  return { stops, routeId, zonaId, truckLabel, today, grandCajas, grandBarriles, skuMap }
}

function buildHtml(data) {
  const { stops, routeId, zonaId, truckLabel, today, grandCajas, grandBarriles, skuMap } = data

  const skuRows = Object.entries(skuMap)
    .map(([sku, d]) => `
      <tr>
        <td>${sku}</td>
        <td>${d.nombre}</td>
        <td style="text-align:center">${d.tipo_envase === 'barril' ? 'Barril' : 'Caja'}</td>
        <td style="text-align:right">${d.total}</td>
      </tr>`)
    .join('')

  const stopRows = stops.map((stop, i) => {
    const productos = stop.client.productos ?? []
    const productLines = productos
      .map(p => `<div style="font-size:11px;color:#475569;margin-top:2px">${p.nombre} — ${p.cantidad_cajas} ${p.tipo_envase === 'barril' ? 'barriles' : 'cajas'}</div>`)
      .join('')
    return `
      <tr>
        <td style="text-align:center;font-weight:700">${i + 1}</td>
        <td style="font-weight:600">${stop.client.name}</td>
        <td style="text-align:center">${stop.arrival_time}</td>
        <td style="text-align:right">${stop._total_boxes ?? 0}</td>
        <td>${productLines}</td>
      </tr>`
  }).join('')

  return `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, Arial, sans-serif; color: #0f172a; font-size: 13px; padding: 32px; }
    .header { background: #c00000; color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }
    .header h1 { font-size: 20px; font-weight: 800; letter-spacing: -0.3px; }
    .header .meta { font-size: 12px; opacity: 0.85; text-align: right; line-height: 1.6; }
    .summary-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 24px; }
    .stat-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; }
    .stat-label { font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
    .stat-value { font-size: 20px; font-weight: 800; color: #0f172a; }
    h2 { font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid #e2e8f0; }
    section { margin-bottom: 28px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { background: #f1f5f9; text-align: left; padding: 8px 10px; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.4px; }
    td { padding: 8px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
    tr:last-child td { border-bottom: none; }
    .footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>Informe de Ruta</h1>
      <div style="font-size:12px;opacity:0.8;margin-top:2px">Damm Smart Truck</div>
    </div>
    <div class="meta">
      ${routeId ? `Ruta: ${routeId}<br/>` : ''}
      ${zonaId ? `Zona: ${zonaId}<br/>` : ''}
      Fecha: ${today}
    </div>
  </div>

  <div class="summary-grid">
    <div class="stat-box">
      <div class="stat-label">Paradas</div>
      <div class="stat-value">${stops.length}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Cajas</div>
      <div class="stat-value">${grandCajas}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Barriles</div>
      <div class="stat-value">${grandBarriles}</div>
    </div>
  </div>

  <section>
    <h2>Productos entregados por SKU</h2>
    <table>
      <thead>
        <tr>
          <th>SKU</th>
          <th>Producto</th>
          <th style="text-align:center">Tipo</th>
          <th style="text-align:right">Unidades</th>
        </tr>
      </thead>
      <tbody>${skuRows}</tbody>
    </table>
  </section>

  <section>
    <h2>Detalle por parada</h2>
    <table>
      <thead>
        <tr>
          <th style="text-align:center;width:36px">#</th>
          <th>Cliente</th>
          <th style="text-align:center;width:60px">Llegada</th>
          <th style="text-align:right;width:60px">Cajas</th>
          <th>Productos</th>
        </tr>
      </thead>
      <tbody>${stopRows}</tbody>
    </table>
  </section>

  <div class="footer">
    Generado el ${today} · ${truckLabel} · Damm Smart Truck
  </div>
</body>
</html>`
}

export async function generateAndShareReport(result) {
  const data = buildReportData(result)
  const html = buildHtml(data)
  const { uri } = await Print.printToFileAsync({ html })
  await Sharing.shareAsync(uri, {
    mimeType: 'application/pdf',
    dialogTitle: 'Guardar informe de ruta',
    UTI: 'com.adobe.pdf',
  })
}
