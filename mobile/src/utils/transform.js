import { MOCK_DEPOT, TRUCK_CONFIGS } from '../constants'

function minutesToHHMM(min) {
  const h = Math.floor(min / 60)
  const m = min % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

const TRUCK_TYPE_MAP = {
  furgoneta: '3pal',
  mediano: '6pal',
  grande: '8pal',
}

function buildLoadPlan(stops, truckType) {
  const cfg = TRUCK_CONFIGS[truckType] || TRUCK_CONFIGS['6pal']
  const items = []
  const sliceSize = (cfg.zHalf * 2) / Math.max(stops.length, 1)
  const zMin = -cfg.zHalf

  stops.forEach((stop, i) => {
    const productos = stop.client.productos || []
    const totalCajas = productos.filter(p => p.tipo_envase === 'caja').reduce((s, p) => s + p.cantidad_cajas, 0)
    const totalBarriles = productos.filter(p => p.tipo_envase === 'barril').reduce((s, p) => s + p.cantidad_cajas, 0)
    const total = totalCajas + totalBarriles
    const barrilRatio = total > 0 ? totalBarriles / total : 0

    const zStart = zMin + i * sliceSize
    const zEnd = zStart + sliceSize - 0.1
    let slot = 0

    for (let x = -cfg.xRange; x <= cfg.xRange; x += 0.4) {
      for (let y = -0.7; y <= 0.4; y += 0.3) {
        for (let z = zStart; z <= zEnd; z += 0.4) {
          const tipo = slot / Math.max(total, 1) < (1 - barrilRatio) ? 'caja' : 'barril'
          items.push({
            id: `pkg_${stop.client.client_id}_${slot}`,
            client_id: stop.client.client_id,
            tipo,
            x: x + (Math.random() * 0.02),
            y: y + (tipo === 'barril' ? 0.1 : 0),
            z: z + (Math.random() * 0.02),
          })
          slot++
        }
      }
    }
  })

  return { items, truck_type: truckType }
}

export function transformSolveResponse(solveResponse) {
  const route = solveResponse.routes?.[0]?.route
  if (!route) throw new Error('No routes in solve response')

  const truckType = TRUCK_TYPE_MAP[route.tipo_camion] || '6pal'

  const stops = route.paradas.map(parada => {
    const clientId = `parada-${parada.orden}`
    const allClientes = parada.clientes || []
    const totalBoxes = allClientes.reduce((s, c) => s + (c.total_cajas || 0), 0)
    const allProductos = allClientes.flatMap(c => c.productos || [])

    let name
    if (allClientes.length === 1) {
      name = allClientes[0].nombre
    } else if (allClientes.length > 1) {
      name = `${allClientes[0].nombre} +${allClientes.length - 1} más`
    } else {
      name = `Parada ${parada.orden + 1}`
    }

    const barriles = allProductos.filter(p => p.tipo_envase === 'barril').reduce((s, p) => s + p.cantidad_cajas, 0)

    return {
      client: {
        client_id: clientId,
        name,
        lat: parada.coordenadas.lat,
        lon: parada.coordenadas.lon,
        priority: 1,
        productos: allProductos,
        time_window: null,
      },
      arrival_time: minutesToHHMM(parada.llegada_min),
      status: 'OK',
      wait_min: 0,
      _barriles_retorno: barriles,
      _total_boxes: totalBoxes,
    }
  })

  const orders = {}
  stops.forEach(stop => {
    orders[stop.client.client_id] = {
      total_boxes: stop._total_boxes,
      productos: stop.client.productos,
    }
  })

  const returnablesPerClient = {}
  stops.forEach(stop => {
    if (stop._barriles_retorno > 0) {
      returnablesPerClient[stop.client.client_id] = stop._barriles_retorno
    }
  })

  const scenario = {
    zone: { depot: MOCK_DEPOT },
    orders,
  }

  const result = {
    route: {
      stops,
      total_distance_km: solveResponse.metrics?.distancia_total_km ?? null,
    },
    load_plan: buildLoadPlan(stops, truckType),
    returnables_plan: { per_client: returnablesPerClient },
  }

  return { scenario, result }
}
