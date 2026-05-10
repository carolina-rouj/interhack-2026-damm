import { View, Text, ScrollView, StyleSheet } from 'react-native'
import { COLORS } from '../constants'

export default function MetricsBar({ metrics }) {
  if (!metrics) return null

  const cards = [
    { label: 'Distancia', value: metrics.total_distance_km, unit: 'km' },
    { label: 'Tiempo ruta', value: `${Math.floor(metrics.total_time_min / 60)}h ${metrics.total_time_min % 60}m`, unit: '' },
    { label: 'Camión', value: `${metrics.truck_utilization_pct}%`, unit: '' },
    { label: 'CO₂', value: metrics.co2_kg, unit: 'kg' },
    { label: 'Paradas', value: metrics.stops_total, unit: '' },
    { label: 'Incumpl.', value: metrics.time_window_violations, unit: '' },
    { label: 'Prior. P1', value: metrics.priority1_served, unit: '' },
    { label: 'Retorn.', value: metrics.returnables_pallets_reserved, unit: 'palés' },
  ]

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.container} contentContainerStyle={styles.content}>
      {cards.map(c => (
        <View key={c.label} style={styles.card}>
          <Text style={styles.label}>{c.label}</Text>
          <Text style={styles.value}>{c.value}</Text>
          {!!c.unit && <Text style={styles.unit}>{c.unit}</Text>}
        </View>
      ))}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { marginBottom: 12 },
  content: { paddingHorizontal: 2, gap: 8, flexDirection: 'row' },
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 12,
    width: 100,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  label: { fontSize: 10, color: COLORS.muted, textAlign: 'center', marginBottom: 4 },
  value: { fontSize: 18, fontWeight: '700', color: COLORS.dark },
  unit: { fontSize: 10, color: COLORS.muted, marginTop: 2 },
})
