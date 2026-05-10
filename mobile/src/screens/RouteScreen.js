import { useState, useEffect } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, useWindowDimensions } from 'react-native'
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps'
import { Check } from 'lucide-react-native'
import Constants from 'expo-constants'
import { COLORS, PRIORITY_COLORS, MOCK_STOPS, MOCK_DEPOT } from '../constants'

const MAPS_API_KEY = Constants.expoConfig?.extra?.googleMapsApiKey

function decodePolyline(encoded) {
  const coords = []
  let index = 0, lat = 0, lng = 0
  while (index < encoded.length) {
    let b, shift = 0, result = 0
    do { b = encoded.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5 } while (b >= 0x20)
    lat += result & 1 ? ~(result >> 1) : result >> 1
    shift = 0; result = 0
    do { b = encoded.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5 } while (b >= 0x20)
    lng += result & 1 ? ~(result >> 1) : result >> 1
    coords.push({ latitude: lat / 1e5, longitude: lng / 1e5 })
  }
  return coords
}

function getBearing(lat1, lon1, lat2, lon2) {
  const φ1 = lat1 * Math.PI / 180
  const φ2 = lat2 * Math.PI / 180
  const Δλ = (lon2 - lon1) * Math.PI / 180
  const y = Math.sin(Δλ) * Math.cos(φ2)
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ)
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360
}

function sampleArrows(coords) {
  const step = Math.max(1, Math.floor(coords.length / 8))
  const arrows = []
  for (let i = step; i < coords.length - 1; i += step) {
    arrows.push({
      coordinate: coords[i],
      rotation: getBearing(coords[i - 1].latitude, coords[i - 1].longitude, coords[i].latitude, coords[i].longitude),
    })
  }
  return arrows
}

async function fetchRouteCoords(depot, stops, apiKey) {
  console.log('[Directions] API key:', apiKey ? 'loaded' : 'MISSING')
  if (!stops.length || !apiKey) return null
  const origin = `${depot.lat},${depot.lon}`
  const waypoints = stops.map(s => `${s.client.lat},${s.client.lon}`).join('|')
  const url = `https://maps.googleapis.com/maps/api/directions/json?origin=${origin}&destination=${origin}&waypoints=${encodeURIComponent(waypoints)}&key=${apiKey}`
  try {
    const res = await fetch(url)
    const data = await res.json()
    console.log('[Directions] status:', data.status, data.error_message ?? '')
    if (data.status !== 'OK') return null
    return decodePolyline(data.routes[0].overview_polyline.points)
  } catch (e) {
    console.log('[Directions] fetch error:', e.message)
    return null
  }
}

function lerpColor(t) {
  const [r1, g1, b1] = t < 0.5 ? [225, 6, 0] : [234, 179, 8]
  const [r2, g2, b2] = t < 0.5 ? [234, 179, 8] : [22, 163, 74]
  const s = t < 0.5 ? t * 2 : (t - 0.5) * 2
  return `rgb(${Math.round(r1 + (r2 - r1) * s)},${Math.round(g1 + (g2 - g1) * s)},${Math.round(b1 + (b2 - b1) * s)})`
}

function lotColor(boxes) {
  if (!boxes) return '#cbd5e1'
  if (boxes <= 10) return '#6ee7b7'
  if (boxes <= 30) return '#fcd34d'
  return '#fb923c'
}

function DeliveryProgressBar({ delivered, total }) {
  const percent = total > 0 ? Math.round((delivered / total) * 100) : 0
  const t = total > 0 ? delivered / total : 0
  const fillColor = lerpColor(t)
  const done = t === 1

  return (
    <View style={styles.progressCard}>
      <View style={styles.progressHeader}>
        <Text style={styles.progressLabel}>
          {done ? 'Ruta completada' : 'Entregas'}
        </Text>
        <Text style={[styles.progressCount, { color: fillColor }]}>
          {delivered} <Text style={styles.progressTotal}>/ {total}</Text>
        </Text>
      </View>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${percent}%`, backgroundColor: fillColor }]} />
      </View>
    </View>
  )
}

function DeliveryStopRow({ stop, index, isDelivered, isCurrent, boxes, onToggle }) {
  const circleColor = isDelivered ? '#cbd5e1' : lotColor(boxes)

  return (
    <TouchableOpacity
      activeOpacity={0.95}
      onPress={() => onToggle(stop.client.client_id)}
      style={[styles.stopRow, isCurrent && styles.stopRowCurrent, isDelivered && styles.stopRowDone]}
    >
      <View style={[styles.numberCircle, { backgroundColor: circleColor }]}>
        {isDelivered
          ? <Check size={16} color="#fff" strokeWidth={3} />
          : <Text style={styles.numberText}>{index + 1}</Text>
        }
      </View>
      <View style={styles.stopInfo}>
        <Text style={[styles.clientName, isDelivered && styles.textDelivered]}>
          {stop.client.name}
        </Text>
        <Text style={styles.stopDetail}>{stop.arrival_time} · P{stop.client.priority}</Text>
      </View>
      <View style={[styles.deliverBtn, isDelivered && styles.deliverBtnDone]}>
        <Text style={styles.deliverBtnText}>
          {isDelivered ? 'Entregado' : 'Entregar'}
        </Text>
      </View>
    </TouchableOpacity>
  )
}

export default function RouteScreen({ scenario, result, deliveredIds, toggleDelivered }) {
  const { width } = useWindowDimensions()
  const [containerHeight, setContainerHeight] = useState(0)
  const [routeCoords, setRouteCoords] = useState(null)

  const stops = result?.route?.stops?.length > 0 ? result.route.stops : MOCK_STOPS
  const depot = scenario?.zone?.depot ?? MOCK_DEPOT
  const orders = scenario?.orders || {}

  const totalStops = stops.length
  const deliveredCount = deliveredIds.size
  const currentStop = stops.find(s => !deliveredIds.has(s.client.client_id))

  useEffect(() => {
    setRouteCoords(null)
    fetchRouteCoords(depot, stops, MAPS_API_KEY)
      .then(coords => { if (coords) setRouteCoords(coords) })
      .catch(() => {})
  }, [depot, stops])

  const region = {
    latitude: depot.lat,
    longitude: depot.lon,
    latitudeDelta: 0.04,
    longitudeDelta: 0.04,
  }

  const fallbackPositions = [
    { latitude: depot.lat, longitude: depot.lon },
    ...stops.map(s => ({ latitude: s.client.lat, longitude: s.client.lon })),
    { latitude: depot.lat, longitude: depot.lon },
  ]

  const pageStyle = { width, height: containerHeight }

  return (
    <View style={styles.screen} onLayout={e => setContainerHeight(e.nativeEvent.layout.height)}>
      {containerHeight > 0 && (
        <ScrollView
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          bounces={false}
          style={styles.pager}
        >
          {/* Page 1: Map */}
          <View style={pageStyle}>
            <View style={styles.mapWrapper}>
              <MapView
                provider={PROVIDER_GOOGLE}
                style={StyleSheet.absoluteFill}
                region={region}
              >
                <Marker
                  coordinate={{ latitude: depot.lat, longitude: depot.lon }}
                  title={depot.name ?? 'Fábrica Damm'}
                  description="Depósito de salida"
                  pinColor={COLORS.dark}
                />
                <Polyline
                  coordinates={routeCoords ?? fallbackPositions}
                  strokeColor="#1e293b"
                  strokeWidth={3}
                  lineDashPattern={routeCoords ? undefined : [8, 5]}
                />
                {sampleArrows(routeCoords ?? fallbackPositions).map((arrow, i) => (
                  <Marker
                    key={`arrow-${i}`}
                    coordinate={arrow.coordinate}
                    rotation={arrow.rotation}
                    anchor={{ x: 0.5, y: 0.5 }}
                    flat
                    tracksViewChanges={false}
                  >
                    <View style={styles.arrowMarker}>
                      <Text style={styles.arrowText}>▲</Text>
                    </View>
                  </Marker>
                ))}
                {stops.map((stop, i) => {
                  const isDelivered = deliveredIds.has(stop.client.client_id)
                  const isCurrent = stop === currentStop
                  const color = isDelivered ? '#94a3b8' : isCurrent ? '#3b82f6' : (PRIORITY_COLORS[stop.client.priority] || COLORS.muted)
                  return (
                    <Marker
                      key={stop.client.client_id}
                      coordinate={{ latitude: stop.client.lat, longitude: stop.client.lon }}
                      title={`${i + 1}. ${stop.client.name}`}
                      description={isDelivered ? 'Entregado' : `Llegada: ${stop.arrival_time}`}
                      pinColor={color}
                    />
                  )
                })}
              </MapView>
            </View>

            <View style={styles.mapBottom}>
              <DeliveryProgressBar delivered={deliveredCount} total={totalStops} />
              <View style={styles.swipeChip}>
                <Text style={styles.swipeChipText}>Desliza para ver paradas →</Text>
              </View>
            </View>
          </View>

          {/* Page 2: Stops */}
          <View style={[pageStyle, styles.stopsPage]}>
            <View style={styles.stopsHeader}>
              <View>
                <Text style={styles.stopsHeaderText}>Paradas</Text>
                <Text style={styles.stopsHeaderSub}>{deliveredCount} de {totalStops} entregadas</Text>
              </View>
            </View>
            <DeliveryProgressBar delivered={deliveredCount} total={totalStops} />
            <ScrollView contentContainerStyle={styles.stopsContent} showsVerticalScrollIndicator={false}>
              {stops.map((stop, i) => (
                <DeliveryStopRow
                  key={stop.client.client_id}
                  stop={stop}
                  index={i}
                  isDelivered={deliveredIds.has(stop.client.client_id)}
                  isCurrent={stop === currentStop}
                  boxes={orders[stop.client.client_id]?.total_boxes}
                  onToggle={toggleDelivered}
                />
              ))}
            </ScrollView>
          </View>
        </ScrollView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#f0f4f8' },
  pager: { flex: 1 },
  mapWrapper: { flex: 1 },

  mapBottom: {
    backgroundColor: '#f0f4f8',
    paddingBottom: 8,
  },

  progressCard: {
    marginHorizontal: 14,
    marginTop: 12,
    marginBottom: 4,
    backgroundColor: '#fff',
    borderRadius: 18,
    paddingHorizontal: 16,
    paddingVertical: 14,
    shadowColor: '#000',
    shadowOpacity: 0.07,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  progressLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#94a3b8',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  progressCount: {
    fontSize: 18,
    fontWeight: '800',
  },
  progressTotal: {
    fontSize: 14,
    fontWeight: '500',
    color: '#94a3b8',
  },
  progressTrack: {
    height: 7,
    backgroundColor: '#e2e8f0',
    borderRadius: 999,
    overflow: 'hidden',
  },
  progressFill: { height: '100%', borderRadius: 999 },

  swipeChip: {
    alignSelf: 'center',
    marginTop: 10,
    marginBottom: 4,
    backgroundColor: '#e2e8f0',
    paddingHorizontal: 32,
    paddingVertical: 8,
    borderRadius: 999,
  },
  swipeChipText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#64748b',
    letterSpacing: 0.5,
  },

  stopsPage: { backgroundColor: '#f0f4f8' },
  stopsHeader: {
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 4,
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
  },
  stopsHeaderText: {
    fontSize: 24,
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: -0.5,
  },
  stopsHeaderSub: {
    fontSize: 13,
    color: '#94a3b8',
    marginTop: 2,
    fontWeight: '500',
  },
  stopsContent: {
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 32,
    gap: 8,
  },

  stopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 14,
    gap: 12,
  },
  stopRowCurrent: {
    borderWidth: 1.5,
    borderColor: '#3b82f6',
    shadowColor: '#3b82f6',
    shadowOpacity: 0.35,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 0 },
    elevation: 6,
  },
  stopRowDone: {
    opacity: 0.5,
  },
  numberCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  numberText: { color: '#fff', fontWeight: '800', fontSize: 13 },
  stopInfo: { flex: 1 },
  clientName: { fontSize: 14, fontWeight: '600', color: '#0f172a' },
  textDelivered: { color: '#94a3b8' },
  stopDetail: { fontSize: 12, color: '#94a3b8', marginTop: 3, fontWeight: '500' },

  deliverBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: '#64748b',
    flexShrink: 0,
  },
  deliverBtnDone: { backgroundColor: '#22c55e' },
  deliverBtnText: { fontSize: 12, fontWeight: '700', color: '#fff' },

  arrowMarker: { alignItems: 'center', justifyContent: 'center' },
  arrowText: { fontSize: 10, color: '#1e293b', lineHeight: 10 },
})
