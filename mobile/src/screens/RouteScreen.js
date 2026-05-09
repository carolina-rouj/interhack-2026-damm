import { View, Text, ScrollView, StyleSheet } from 'react-native'
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps'
import ControlPanel from '../components/ControlPanel'
import MetricsBar from '../components/MetricsBar'
import StopsList from '../components/StopsList'
import { COLORS, PRIORITY_COLORS } from '../constants'

export default function RouteScreen(props) {
  const { scenario, result } = props
  const stops = result?.route?.stops || []
  const orders = scenario?.orders || {}
  const depot = scenario?.zone?.depot

  const hasMap = stops.length > 0 && depot

  const region = hasMap
    ? {
        latitude: depot.lat,
        longitude: depot.lon,
        latitudeDelta: 0.04,
        longitudeDelta: 0.04,
      }
    : null

  const positions = hasMap
    ? [
        { latitude: depot.lat, longitude: depot.lon },
        ...stops.map(s => ({ latitude: s.client.lat, longitude: s.client.lon })),
        { latitude: depot.lat, longitude: depot.lon },
      ]
    : []

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <ControlPanel {...props} />

      {hasMap ? (
        <View style={styles.mapCard}>
          <MapView
            provider={PROVIDER_GOOGLE}
            style={styles.map}
            region={region}
          >
            <Marker
              coordinate={{ latitude: depot.lat, longitude: depot.lon }}
              title="Fabrica Damm"
              description="Deposito de salida"
              pinColor={COLORS.dark}
            />

            <Polyline
              coordinates={positions}
              strokeColor={COLORS.dark}
              strokeWidth={2.5}
              lineDashPattern={[6, 4]}
            />

            {stops.map((stop, i) => {
              const isViolated = stop.status === 'TIME_WINDOW_VIOLATED'
              const color = isViolated ? '#b91c1c' : (PRIORITY_COLORS[stop.client.priority] || COLORS.muted)
              return (
                <Marker
                  key={stop.client.client_id}
                  coordinate={{ latitude: stop.client.lat, longitude: stop.client.lon }}
                  title={`${i + 1}. ${stop.client.name}`}
                  description={`Llegada: ${stop.arrival_time} | ${isViolated ? 'INCUMPLIDO' : stop.wait_min > 0 ? `Espera: ${stop.wait_min} min` : 'OK'}`}
                  pinColor={color}
                />
              )
            })}
          </MapView>
        </View>
      ) : (
        !props.loading && !scenario && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>🚛</Text>
            <Text style={styles.emptyTitle}>DAMM Smart Truck</Text>
            <Text style={styles.emptyText}>Genera un escenario y optimiza la ruta y la carga del camión.</Text>
          </View>
        )
      )}

      {result && (
        <>
          <MetricsBar metrics={result.metrics} />
          <StopsList stops={stops} orders={orders} />
        </>
      )}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.bg },
  content: { padding: 12 },
  mapCard: {
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 4,
  },
  map: { height: 320 },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 48,
    paddingHorizontal: 32,
  },
  emptyIcon: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 20, fontWeight: '700', color: COLORS.dark, marginBottom: 8 },
  emptyText: { fontSize: 14, color: COLORS.muted, textAlign: 'center', lineHeight: 20 },
})
