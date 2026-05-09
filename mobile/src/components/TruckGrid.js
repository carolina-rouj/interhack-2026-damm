import { View, Text, StyleSheet } from 'react-native'
import { COLORS, PALETTE } from '../constants'

function isLight(hex) {
  const c = hex.replace('#', '')
  const r = parseInt(c.substr(0, 2), 16)
  const g = parseInt(c.substr(2, 2), 16)
  const b = parseInt(c.substr(4, 2), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 > 160
}

function PalletCell({ slotId, slotMap, clientColorMap }) {
  const assignments = slotMap[slotId] || []
  const isRetorn = assignments.some(a => a.is_returnable_buffer)

  if (isRetorn) {
    return (
      <View style={[styles.cell, { backgroundColor: '#f3f4f6' }]}>
        <Text style={[styles.slotNum, { color: COLORS.muted }]}>P{slotId}</Text>
        <Text style={{ fontSize: 16 }}>📦</Text>
        <Text style={[styles.clientLabel, { color: COLORS.muted }]}>RETORN</Text>
        <Text style={[styles.boxesLabel, { color: COLORS.muted }]}>reservado</Text>
      </View>
    )
  }

  if (assignments.length === 0) {
    return (
      <View style={[styles.cell, { backgroundColor: '#f9fafb' }]}>
        <Text style={[styles.slotNum, { color: '#9ca3af' }]}>P{slotId}</Text>
        <Text style={{ fontSize: 12, color: '#9ca3af' }}>vacío</Text>
      </View>
    )
  }

  const primary = assignments[0]
  const color = clientColorMap[primary.client_id] || '#e5e7eb'
  const textColor = isLight(color) ? COLORS.dark : '#fff'
  const isSplit = assignments.length > 1

  return (
    <View style={[styles.cell, { backgroundColor: color }]}>
      <Text style={[styles.slotNum, { color: textColor, opacity: 0.7 }]}>P{slotId}</Text>
      {primary.delivery_position > 0 && (
        <Text style={[styles.deliveryPos, { color: textColor }]}>#{primary.delivery_position}</Text>
      )}
      <Text style={[styles.clientLabel, { color: textColor }]} numberOfLines={2}>
        {assignments.map(a => a.client_name?.split(' ').slice(-1)[0]).join(' / ')}
      </Text>
      <Text style={[styles.boxesLabel, { color: textColor }]}>
        {assignments.map(a => `${a.boxes}`).join('+')} cajas
      </Text>
      {isSplit && <Text style={[styles.splitLabel, { color: textColor }]}>split</Text>}
    </View>
  )
}

export default function TruckGrid({ loadPlan, stops }) {
  if (!loadPlan) return null

  const clientColorMap = {}
  if (stops) {
    stops.forEach((stop, i) => {
      clientColorMap[stop.client.client_id] = PALETTE[i % PALETTE.length]
    })
  }

  const slotMap = {}
  loadPlan.assignments.forEach(a => {
    const id = a.slot.slot_id
    if (!slotMap[id]) slotMap[id] = []
    slotMap[id].push(a)
  })

  const slotOrder = [1, 2, 3, 4, 5, 6]

  const legendItems = stops
    ? stops.map((stop, i) => ({
        clientId: stop.client.client_id,
        name: stop.client.name,
        color: PALETTE[i % PALETTE.length],
        pos: i + 1,
      }))
    : []

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>Distribución de palés</Text>

      <View style={styles.truckWrap}>
        <Text style={styles.truckLabel}>Puerta trasera (descarga)</Text>
        <View style={styles.truckWithSides}>
          <Text style={styles.sideLabel}>Lona lateral</Text>
          <View style={styles.grid}>
            {slotOrder.map(id => (
              <PalletCell key={id} slotId={id} slotMap={slotMap} clientColorMap={clientColorMap} />
            ))}
          </View>
          <Text style={styles.sideLabel}>Lona lateral</Text>
        </View>
        <Text style={styles.truckLabel}>Cabina conductor</Text>
      </View>

      {loadPlan.warnings?.length > 0 && (
        <View style={styles.warningsBox}>
          <Text style={styles.warningsTitle}>Avisos de carga</Text>
          {loadPlan.warnings.map((w, i) => (
            <Text key={i} style={styles.warningItem}>{w}</Text>
          ))}
        </View>
      )}

      <View style={styles.legend}>
        <Text style={styles.legendTitle}>Leyenda</Text>
        {legendItems.map(item => (
          <View key={item.clientId} style={styles.legendRow}>
            <View style={[styles.legendDot, { backgroundColor: item.color }]} />
            <Text style={styles.legendText}>{item.pos}. {item.name}</Text>
          </View>
        ))}
        <View style={styles.legendRow}>
          <View style={[styles.legendDot, { backgroundColor: '#f3f4f6', borderWidth: 1, borderColor: '#d1d5db' }]} />
          <Text style={styles.legendText}>Retornables</Text>
        </View>
      </View>
    </View>
  )
}

const CELL_SIZE = '47%'

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
  sectionLabel: { fontSize: 14, fontWeight: '700', color: COLORS.dark, marginBottom: 12 },
  truckWrap: { alignItems: 'center', marginBottom: 16 },
  truckLabel: { fontSize: 11, color: COLORS.muted, marginVertical: 4, textAlign: 'center' },
  truckWithSides: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  sideLabel: {
    fontSize: 10, color: COLORS.muted, textAlign: 'center', width: 20,
    transform: [{ rotate: '90deg' }],
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', width: 220, gap: 4 },
  cell: {
    width: CELL_SIZE, height: 90, borderRadius: 8,
    padding: 6, alignItems: 'center', justifyContent: 'center',
  },
  slotNum: { fontSize: 9, fontWeight: '700', alignSelf: 'flex-start' },
  deliveryPos: { fontSize: 9, fontWeight: '600' },
  clientLabel: { fontSize: 9, fontWeight: '700', textAlign: 'center', lineHeight: 12 },
  boxesLabel: { fontSize: 9, textAlign: 'center' },
  splitLabel: { fontSize: 8, opacity: 0.7 },
  warningsBox: {
    backgroundColor: '#fff7ed',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  warningsTitle: { fontSize: 12, fontWeight: '700', color: COLORS.orange, marginBottom: 4 },
  warningItem: { fontSize: 11, color: COLORS.dark, marginBottom: 2 },
  legend: { gap: 4 },
  legendTitle: { fontSize: 12, fontWeight: '700', color: COLORS.dark, marginBottom: 4 },
  legendRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  legendDot: { width: 12, height: 12, borderRadius: 6 },
  legendText: { fontSize: 11, color: COLORS.dark },
})
