import { useState, useEffect, useRef } from 'react'
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  useWindowDimensions, Alert, ActivityIndicator,
} from 'react-native'
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps'
import * as Location from 'expo-location'
import { Check, Navigation } from 'lucide-react-native'
import { COLORS, PRIORITY_COLORS } from '../constants'
import { fetchRouteLegs } from '../services/directionsService'

const GOOGLE_MAPS_API_KEY = 'YOUR_GOOGLE_MAPS_API_KEY'

const MOCK_DEPOT = { lat: 41.4065, lon: 2.1878, name: 'Fábrica Damm' }

const MOCK_STOPS = [
  { client: { client_id: 'm1', name: 'Bar El Xampanyet', lat: 41.3847, lon: 2.1834, priority: 1, time_window: { open_min: 480, close_min: 600 } }, arrival_time: '09:15', status: 'OK', wait_min: 0 },
  { client: { client_id: 'm2', name: 'Restaurant La Pepita', lat: 41.3901, lon: 2.1701, priority: 2, time_window: { open_min: 540, close_min: 660 } }, arrival_time: '09:45', status: 'OK', wait_min: 5 },
  { client: { client_id: 'm3', name: 'Cafetería Central', lat: 41.4010, lon: 2.1750, priority: 3, time_window: { open_min: 600, close_min: 720 } }, arrival_time: '10:20', status: 'OK', wait_min: 0 },
  { client: { client_id: 'm4', name: 'Hotel Arts Bar', lat: 41.3870, lon: 2.1970, priority: 1, time_window: { open_min: 480, close_min: 570 } }, arrival_time: '10:50', status: 'TIME_WINDOW_VIOLATED', wait_min: 0 },
  { client: { client_id: 'm5', name: 'Terraza Barceloneta', lat: 41.3790, lon: 2.1900, priority: 2, time_window: { open_min: 660, close_min: 780 } }, arrival_time: '11:30', status: 'OK', wait_min: 0 },
]

function haversineM(lat1, lon1, lat2, lon2) {
  const R = 6371e3
  const φ1 = (lat1 * Math.PI) / 180
  const φ2 = (lat2 * Math.PI) / 180
  const Δφ = ((lat2 - lat1) * Math.PI) / 180
  const Δλ = ((lon2 - lon1) * Math.PI) / 180
  const a = Math.sin(Δφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function formatDist(meters) {
  if (meters == null) return null
  return meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`
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
        <Text style={styles.progressLabel}>{done ? 'Ruta completada' : 'Entregas'}</Text>
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
        <Text style={[styles.clientName, isDelivered && styles.textDelivered]}>{stop.client.name}</Text>
        <Text style={styles.stopDetail}>{stop.arrival_time} · P{stop.client.priority}</Text>
      </View>
      <View style={[styles.deliverBtn, isDelivered && styles.deliverBtnDone]}>
        <Text style={styles.deliverBtnText}>{isDelivered ? 'Entregado' : 'Entregar'}</Text>
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
  const [navState, setNavState] = useState('preview')
  const [currentStopIndex, setCurrentStopIndex] = useState(0)
  const [driverLocation, setDriverLocation] = useState(null)
  const [routeLegs, setRouteLegs] = useState([])
  const [loadingLegs, setLoadingLegs] = useState(false)

  const mapRef = useRef(null)
  const locationSub = useRef(null)

  useEffect(() => {
    setDeliveredIds(new Set())
    setNavState('preview')
    setCurrentStopIndex(0)
  }, [result])

  useEffect(() => {
    if (!stops.length) return
    setLoadingLegs(true)
    fetchRouteLegs(depot, stops, GOOGLE_MAPS_API_KEY)
      .then(setRouteLegs)
      .finally(() => setLoadingLegs(false))
  }, [result])

  useEffect(() => {
    if (navState === 'navigating' && driverLocation) {
      mapRef.current?.animateToRegion(
        { ...driverLocation, latitudeDelta: 0.005, longitudeDelta: 0.005 },
        800,
      )
    }
  }, [driverLocation, navState])

  useEffect(() => {
    return () => { locationSub.current?.remove() }
  }, [])

  function stopTracking() {
    locationSub.current?.remove()
    locationSub.current = null
  }

  async function handleInitiate() {
    const { status } = await Location.requestForegroundPermissionsAsync()
    if (status !== 'granted') {
      Alert.alert('Permiso denegado', 'Necesitas permitir el acceso a la ubicación para iniciar la navegación.')
      return
    }

    const sub = await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.High, timeInterval: 2000, distanceInterval: 10 },
      loc => setDriverLocation({ latitude: loc.coords.latitude, longitude: loc.coords.longitude }),
    )
    locationSub.current = sub

    setCurrentStopIndex(0)
    setDeliveredIds(new Set())
    setNavState('navigating')
  }

  function handleDelivered() {
    const deliveredId = stops[currentStopIndex].client.client_id
    setDeliveredIds(prev => new Set([...prev, deliveredId]))
    if (currentStopIndex + 1 >= stops.length) {
      stopTracking()
      setNavState('completed')
    } else {
      setCurrentStopIndex(i => i + 1)
    }
  }

  function handleAbandon() {
    Alert.alert('Abandonar ruta', '¿Seguro que quieres salir de la navegación?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Salir', style: 'destructive', onPress: () => {
          stopTracking()
          setNavState('preview')
          setCurrentStopIndex(0)
          setDriverLocation(null)
        },
      },
    ])
  }

  function handleFinalize() {
    stopTracking()
    setNavState('preview')
    setCurrentStopIndex(0)
    setDriverLocation(null)
  }

  const totalStops = stops.length
  const deliveredCount = deliveredIds.size

  const remainingPolyline = routeLegs.slice(currentStopIndex).flat()

  const previewPolyline = routeLegs.flat().length > 0
    ? routeLegs.flat()
    : [
        { latitude: depot.lat, longitude: depot.lon },
        ...stops.map(s => ({ latitude: s.client.lat, longitude: s.client.lon })),
        { latitude: depot.lat, longitude: depot.lon },
      ]

  const previewRegion = {
    latitude: depot.lat,
    longitude: depot.lon,
    latitudeDelta: 0.04,
    longitudeDelta: 0.04,
  }

  const currentStop = navState === 'navigating' ? stops[currentStopIndex] : null
  const distToCurrentStop = driverLocation && currentStop
    ? haversineM(driverLocation.latitude, driverLocation.longitude, currentStop.client.lat, currentStop.client.lon)
    : null

  const pageStyle = { width, height: containerHeight }

  if (navState === 'navigating') {
    return (
      <View style={styles.screen}>
        <MapView
          ref={mapRef}
          provider={PROVIDER_GOOGLE}
          style={StyleSheet.absoluteFill}
          initialRegion={previewRegion}
          showsUserLocation
          showsMyLocationButton={false}
        >
          <Marker
            coordinate={{ latitude: depot.lat, longitude: depot.lon }}
            title={depot.name ?? 'Fábrica Damm'}
            pinColor={COLORS.dark}
          />
          {remainingPolyline.length > 1 && (
            <Polyline
              coordinates={remainingPolyline}
              strokeColor="#3b82f6"
              strokeWidth={4}
            />
          )}
          {stops.map((stop, i) => {
            const isDelivered = deliveredIds.has(stop.client.client_id)
            const isCurrent = i === currentStopIndex
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

        <View style={styles.navCard}>
          <View style={styles.navCardTop}>
            <View style={styles.navStopBadge}>
              <Navigation size={13} color="#3b82f6" />
              <Text style={styles.navStopBadgeText}>
                Parada {currentStopIndex + 1}/{totalStops}
                {distToCurrentStop != null ? `  ·  ${formatDist(distToCurrentStop)}` : ''}
              </Text>
            </View>
            <Text style={styles.navClientName}>{currentStop?.client.name}</Text>
            <Text style={styles.navArrival}>Llegada estimada: {currentStop?.arrival_time}</Text>
          </View>

          <TouchableOpacity style={styles.deliveredBtn} onPress={handleDelivered} activeOpacity={0.85}>
            <Check size={18} color="#fff" strokeWidth={3} />
            <Text style={styles.deliveredBtnText}>Entregado</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.abandonBtn} onPress={handleAbandon} activeOpacity={0.7}>
            <Text style={styles.abandonBtnText}>Abandonar ruta</Text>
          </TouchableOpacity>
        </View>
      </View>
    )
  }

  if (navState === 'completed') {
    return (
      <View style={[styles.screen, styles.completedScreen]}>
        <MapView
          provider={PROVIDER_GOOGLE}
          style={StyleSheet.absoluteFill}
          region={previewRegion}
          scrollEnabled={false}
          zoomEnabled={false}
        >
          {stops.map((stop, i) => (
            <Marker
              key={stop.client.client_id}
              coordinate={{ latitude: stop.client.lat, longitude: stop.client.lon }}
              title={`${i + 1}. ${stop.client.name}`}
              pinColor="#94a3b8"
            />
          ))}
          {previewPolyline.length > 1 && (
            <Polyline coordinates={previewPolyline} strokeColor="#94a3b8" strokeWidth={3} />
          )}
        </MapView>

        <View style={styles.completedCard}>
          <View style={styles.completedCheck}>
            <Check size={32} color="#22c55e" strokeWidth={3} />
          </View>
          <Text style={styles.completedTitle}>Ruta completada</Text>
          <Text style={styles.completedSub}>
            {totalStops} paradas entregadas
            {result?.route?.total_distance_km ? ` · ${result.route.total_distance_km.toFixed(1)} km` : ''}
          </Text>
          <TouchableOpacity style={styles.finalizeBtn} onPress={handleFinalize} activeOpacity={0.85}>
            <Text style={styles.finalizeBtnText}>Finalizar ruta</Text>
          </TouchableOpacity>
        </View>
      </View>
    )
  }

  // Preview mode
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
                ref={mapRef}
                provider={PROVIDER_GOOGLE}
                style={StyleSheet.absoluteFill}
                region={previewRegion}
              >
                <Marker
                  coordinate={{ latitude: depot.lat, longitude: depot.lon }}
                  title={depot.name ?? 'Fábrica Damm'}
                  description="Depósito de salida"
                  pinColor={COLORS.dark}
                />
                {previewPolyline.length > 1 && (
                  <Polyline
                    coordinates={previewPolyline}
                    strokeColor="#1e293b"
                    strokeWidth={3}
                    lineDashPattern={loadingLegs ? [8, 5] : undefined}
                  />
                )}
                {stops.map((stop, i) => {
                  const color = PRIORITY_COLORS[stop.client.priority] || COLORS.muted
                  return (
                    <Marker
                      key={stop.client.client_id}
                      coordinate={{ latitude: stop.client.lat, longitude: stop.client.lon }}
                      title={`${i + 1}. ${stop.client.name}`}
                      description={`Llegada: ${stop.arrival_time}`}
                      pinColor={color}
                    />
                  )
                })}
              </MapView>

              {loadingLegs && (
                <View style={styles.loadingOverlay}>
                  <ActivityIndicator size="small" color="#3b82f6" />
                  <Text style={styles.loadingText}>Calculando ruta...</Text>
                </View>
              )}
            </View>

            <View style={styles.mapBottom}>
              <DeliveryProgressBar delivered={deliveredCount} total={totalStops} />
              <TouchableOpacity
                style={[styles.initiateBtn, loadingLegs && styles.initiateBtnDisabled]}
                onPress={handleInitiate}
                activeOpacity={0.85}
                disabled={loadingLegs}
              >
                <Navigation size={16} color="#fff" />
                <Text style={styles.initiateBtnText}>Iniciar Ruta</Text>
              </TouchableOpacity>
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
                  isCurrent={stop.client.client_id === stops[0]?.client.client_id && deliveredIds.size === 0}
                  boxes={orders[stop.client.client_id]?.total_boxes}
                  onToggle={id => setDeliveredIds(prev => {
                    const next = new Set(prev)
                    next.has(id) ? next.delete(id) : next.add(id)
                    return next
                  })}
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

  loadingOverlay: {
    position: 'absolute',
    top: 12,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(255,255,255,0.92)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  loadingText: { fontSize: 12, fontWeight: '600', color: '#3b82f6' },

  mapBottom: {
    backgroundColor: '#f0f4f8',
    paddingBottom: 8,
  },

  initiateBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginHorizontal: 14,
    marginTop: 10,
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: '#3b82f6',
    shadowColor: '#3b82f6',
    shadowOpacity: 0.4,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  initiateBtnDisabled: { opacity: 0.55 },
  initiateBtnText: { fontSize: 15, fontWeight: '700', color: '#fff', letterSpacing: 0.3 },

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
  progressCount: { fontSize: 18, fontWeight: '800' },
  progressTotal: { fontSize: 14, fontWeight: '500', color: '#94a3b8' },
  progressTrack: { height: 7, backgroundColor: '#e2e8f0', borderRadius: 999, overflow: 'hidden' },
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
  swipeChipText: { fontSize: 11, fontWeight: '600', color: '#64748b', letterSpacing: 0.5 },

  stopsPage: { backgroundColor: '#f0f4f8' },
  stopsHeader: {
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 4,
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
  },
  stopsHeaderText: { fontSize: 24, fontWeight: '800', color: '#0f172a', letterSpacing: -0.5 },
  stopsHeaderSub: { fontSize: 13, color: '#94a3b8', marginTop: 2, fontWeight: '500' },
  stopsContent: { paddingHorizontal: 14, paddingTop: 10, paddingBottom: 32, gap: 8 },

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
  stopRowDone: { opacity: 0.5 },
  numberCircle: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
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

  // Navigation mode
  navCard: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 32,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: -4 },
    elevation: 12,
  },
  navCardTop: { marginBottom: 18 },
  navStopBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginBottom: 6,
  },
  navStopBadgeText: { fontSize: 12, fontWeight: '700', color: '#3b82f6', letterSpacing: 0.4 },
  navClientName: { fontSize: 20, fontWeight: '800', color: '#0f172a', letterSpacing: -0.3 },
  navArrival: { fontSize: 13, color: '#64748b', marginTop: 4, fontWeight: '500' },

  deliveredBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#22c55e',
    borderRadius: 16,
    paddingVertical: 16,
    shadowColor: '#22c55e',
    shadowOpacity: 0.4,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  deliveredBtnText: { fontSize: 16, fontWeight: '800', color: '#fff' },

  abandonBtn: { alignItems: 'center', marginTop: 14 },
  abandonBtnText: { fontSize: 13, fontWeight: '600', color: '#94a3b8' },

  // Completed mode
  completedScreen: {},
  completedCard: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: 20,
    paddingTop: 28,
    paddingBottom: 40,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: -4 },
    elevation: 12,
  },
  completedCheck: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#dcfce7',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  completedTitle: { fontSize: 22, fontWeight: '800', color: '#0f172a', marginBottom: 6 },
  completedSub: { fontSize: 14, color: '#64748b', fontWeight: '500', marginBottom: 28 },
  finalizeBtn: {
    backgroundColor: '#0f172a',
    borderRadius: 16,
    paddingVertical: 16,
    paddingHorizontal: 40,
  },
  finalizeBtnText: { fontSize: 15, fontWeight: '700', color: '#fff' },
})
