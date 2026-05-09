const DIRECTIONS_URL = 'https://maps.googleapis.com/maps/api/directions/json'

function decodePolyline(encoded) {
  const result = []
  let index = 0
  let lat = 0
  let lng = 0

  while (index < encoded.length) {
    let shift = 0
    let result_lat = 0
    let b
    do {
      b = encoded.charCodeAt(index++) - 63
      result_lat |= (b & 0x1f) << shift
      shift += 5
    } while (b >= 0x20)
    const dlat = result_lat & 1 ? ~(result_lat >> 1) : result_lat >> 1
    lat += dlat

    shift = 0
    let result_lng = 0
    do {
      b = encoded.charCodeAt(index++) - 63
      result_lng |= (b & 0x1f) << shift
      shift += 5
    } while (b >= 0x20)
    const dlng = result_lng & 1 ? ~(result_lng >> 1) : result_lng >> 1
    lng += dlng

    result.push({ latitude: lat / 1e5, longitude: lng / 1e5 })
  }

  return result
}

function straightLegFallback(fromLat, fromLon, toLat, toLon) {
  return [
    { latitude: fromLat, longitude: fromLon },
    { latitude: toLat, longitude: toLon },
  ]
}

export async function fetchRouteLegs(depot, stops, apiKey) {
  if (!apiKey || apiKey === 'YOUR_GOOGLE_MAPS_API_KEY' || !stops.length) {
    return buildStraightLegs(depot, stops)
  }

  const origin = `${depot.lat},${depot.lon}`
  const destination = `${stops[stops.length - 1].client.lat},${stops[stops.length - 1].client.lon}`
  const waypoints = stops
    .slice(0, -1)
    .map(s => `${s.client.lat},${s.client.lon}`)
    .join('|')

  const url =
    `${DIRECTIONS_URL}?origin=${origin}&destination=${destination}` +
    (waypoints ? `&waypoints=${encodeURIComponent(waypoints)}` : '') +
    `&mode=driving&key=${apiKey}`

  try {
    const response = await fetch(url)
    const data = await response.json()

    if (data.status !== 'OK' || !data.routes?.length) {
      return buildStraightLegs(depot, stops)
    }

    const legs = data.routes[0].legs
    return legs.map(leg =>
      leg.steps.flatMap(step => decodePolyline(step.polyline.points))
    )
  } catch {
    return buildStraightLegs(depot, stops)
  }
}

function buildStraightLegs(depot, stops) {
  const legs = []
  let prevLat = depot.lat
  let prevLon = depot.lon
  for (const stop of stops) {
    legs.push(straightLegFallback(prevLat, prevLon, stop.client.lat, stop.client.lon))
    prevLat = stop.client.lat
    prevLon = stop.client.lon
  }
  return legs
}
