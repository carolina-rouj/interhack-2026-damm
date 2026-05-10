import { View, Text, FlatList, StyleSheet } from 'react-native'
import { COLORS, PRIORITY_COLORS } from '../constants'

function fmtMin(m) {
  return `${Math.floor(m / 60).toString().padStart(2, '0')}:${(m % 60).toString().padStart(2, '0')}`
}

function StopRow({ stop, index, orders }) {
  const tw = stop.client.time_window
  const isViolated = stop.status === 'TIME_WINDOW_VIOLATED'
  const hasWait = stop.wait_min > 0
  const order = orders?.[stop.client.client_id]

  const badgeStyle = isViolated ? styles.badgeRed : hasWait ? styles.badgeYellow : styles.badgeGreen
  const badgeText = isViolated ? 'Incumplido' : hasWait ? 'Espera' : 'Correcto'

  return (
    <View style={styles.row}>
      <View style={[styles.numberCircle, { backgroundColor: PRIORITY_COLORS[stop.client.priority] || COLORS.muted }]}>
        <Text style={styles.numberText}>{index + 1}</Text>
      </View>
      <View style={styles.info}>
        <Text style={styles.clientName}>{stop.client.name}</Text>
        <Text style={styles.detail}>
          Ventana: {fmtMin(tw.open_min)}–{fmtMin(tw.close_min)}  |  Llegada: {stop.arrival_time}
        </Text>
        {order && <Text style={styles.detail}>{order.total_boxes} cajas</Text>}
      </View>
      <View style={[styles.badge, badgeStyle]}>
        <Text style={styles.badgeText}>{badgeText}</Text>
      </View>
    </View>
  )
}

export default function StopsList({ stops, orders }) {
  if (!stops || stops.length === 0) return null

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Paradas ({stops.length})</Text>
      <FlatList
        data={stops}
        keyExtractor={item => item.client.client_id}
        renderItem={({ item, index }) => <StopRow stop={item} index={index} orders={orders} />}
        scrollEnabled={false}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  title: { fontSize: 14, fontWeight: '700', color: COLORS.dark, marginBottom: 12 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  numberCircle: {
    width: 28, height: 28, borderRadius: 14,
    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  numberText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  info: { flex: 1 },
  clientName: { fontSize: 13, fontWeight: '600', color: COLORS.dark },
  detail: { fontSize: 11, color: COLORS.muted, marginTop: 2 },
  badge: { borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, flexShrink: 0 },
  badgeText: { fontSize: 10, fontWeight: '600', color: '#fff' },
  badgeGreen: { backgroundColor: COLORS.green },
  badgeYellow: { backgroundColor: COLORS.yellow },
  badgeRed: { backgroundColor: COLORS.red },
  separator: { height: 10 },
})
