import { useState, useEffect } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, useWindowDimensions } from 'react-native'
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps'
import { Check } from 'lucide-react-native'
import { COLORS, PRIORITY_COLORS } from '../constants'

const MOCK_DEPOT = { lat: 41.4065, lon: 2.1878, name: 'Fábrica Damm' }

const MOCK_STOPS = [
  { client: { client_id: 'm1', name: 'Bar El Xampanyet', lat: 41.3847, lon: 2.1834, priority: 1, time_window: { open_min: 480, close_min: 600 } }, arrival_time: '09:15', status: 'OK', wait_min: 0 },
  { client: { client_id: 'm2', name: 'Restaurant La Pepita', lat: 41.3901, lon: 2.1701, priority: 2, time_window: { open_min: 540, close_min: 660 } }, arrival_time: '09:45', status: 'OK', wait_min: 5 },
  { client: { client_id: 'm3', name: 'Cafetería Central', lat: 41.4010, lon: 2.1750, priority: 3, time_window: { open_min: 600, close_min: 720 } }, arrival_time: '10:20', status: 'OK', wait_min: 0 },
  { client: { client_id: 'm4', name: 'Hotel Arts Bar', lat: 41.3870, lon: 2.1970, priority: 1, time_window: { open_min: 480, close_min: 570 } }, arrival_time: '10:50', status: 'TIME_WINDOW_VIOLATED', wait_min: 0 },
  { client: { client_id: 'm5', name: 'Terraza Barceloneta', lat: 41.3790, lon: 2.1900, priority: 2, time_window: { open_min: 660, close_min: 780 } }, arrival_time: '11:30', status: 'OK', wait_min: 0 },
]

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

export default function RouteScreen({ scenario, result }) {
  const { width } = useWindowDimensions()
  const [containerHeight, setContainerHeight] = useState(0)

  const stops = result?.route?.stops?.length > 0 ? result.route.stops : MOCK_STOPS
  const depot = scenario?.zone?.depot ?? MOCK_DEPOT
  const orders = scenario?.orders || {}

  const [deliveredIds, setDeliveredIds] = useState(new Set())

  useEffect(() => {
    setDeliveredIds(new Set())
  }, [result])

  function toggleDelivered(clientId) {
    setDeliveredIds(prev => {
      const next = new Set(prev)
      next.has(clientId) ? next.delete(clientId) : next.add(clientId)
      return next
    })
  }

  const totalStops = stops.length
  const deliveredCount = deliveredIds.size
  const currentStop = stops.find(s => !deliveredIds.has(s.client.client_id))

  const region = {
    latitude: depot.lat,
    longitude: depot.lon,
    latitudeDelta: 0.04,
    longitudeDelta: 0.04,
  }

  const positions = [
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
                  coordinates={positions}
                  strokeColor="#1e293b"
                  strokeWidth={3}
                  lineDashPattern={[8, 5]}
                />
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
})
