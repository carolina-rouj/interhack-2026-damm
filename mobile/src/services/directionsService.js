const DIRECTIONS_URL = 'https://maps.googleapis.com/maps/api/directions/json'

function decodePolyline(encoded) {
  const result = []
  let index = 0, lat = 0, lng = 0
  while (index < encoded.length) {
    let shift = 0, result_lat = 0, b
    do { b = encoded.charCodeAt(index++) - 63; result_lat |= (b & 0x1f) << shift; shift += 5 } while (b >= 0x20)
    lat += result_lat & 1 ? ~(result_lat >> 1) : result_lat >> 1
    shift = 0
    let result_lng = 0
    do { b = encoded.charCodeAt(index++) - 63; result_lng |= (b & 0x1f) << shift; shift += 5 } while (b >= 0x20)
    lng += result_lng & 1 ? ~(result_lng >> 1) : result_lng >> 1
    result.push({ latitude: lat / 1e5, longitude: lng / 1e5 })
  }
  return result
}

function buildStraightLegs(depot, stops) {
  const legs = []
  let prevLat = depot.lat, prevLon = depot.lon
  for (const stop of stops) {
    legs.push([
      { latitude: prevLat, longitude: prevLon },
      { latitude: stop.client.lat, longitude: stop.client.lon },
    ])
    prevLat = stop.client.lat
    prevLon = stop.client.lon
  }
  return legs
}

export async function fetchRouteLegs(depot, stops, apiKey) {
  if (!apiKey || !stops.length) return buildStraightLegs(depot, stops)

  const origin = `${depot.lat},${depot.lon}`
  const destination = `${stops[stops.length - 1].client.lat},${stops[stops.length - 1].client.lon}`
  const waypoints = stops.slice(0, -1).map(s => `${s.client.lat},${s.client.lon}`).join('|')
  const url = `${DIRECTIONS_URL}?origin=${origin}&destination=${destination}` +
    (waypoints ? `&waypoints=${encodeURIComponent(waypoints)}` : '') +
    `&mode=driving&key=${apiKey}`

  try {
    const res = await fetch(url)
    const data = await res.json()
    if (data.status !== 'OK' || !data.routes?.length) return buildStraightLegs(depot, stops)
    return data.routes[0].legs.map(leg =>
      leg.steps.flatMap(step => decodePolyline(step.polyline.points))
    )
  } catch {
    return buildStraightLegs(depot, stops)
  }
}
