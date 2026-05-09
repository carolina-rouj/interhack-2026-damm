import { View, Text, FlatList, StyleSheet } from 'react-native'
import { COLORS } from '../constants'

function rowLabel(row) {
  if (row === 1) return 'Trasera'
  if (row === 2) return 'Central'
  return 'Delantera'
}

export default function LoadTable({ loadPlan }) {
  if (!loadPlan) return null

  const sorted = [...loadPlan.assignments].sort((a, b) => a.slot.slot_id - b.slot.slot_id)

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Detalle de asignación</Text>
      <FlatList
        data={sorted}
        keyExtractor={(_, i) => String(i)}
        scrollEnabled={false}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        renderItem={({ item: a }) => (
          <View style={styles.row}>
            <View style={styles.pallet}>
              <Text style={styles.palletText}>P{a.slot.slot_id}</Text>
            </View>
            <View style={styles.info}>
              <Text style={styles.zone}>{rowLabel(a.slot.row)}</Text>
              {a.is_returnable_buffer
                ? <View style={styles.retornBadge}><Text style={styles.retornText}>Retornables</Text></View>
                : <Text style={styles.clientName}>{a.client_name}</Text>
              }
            </View>
            <View style={styles.right}>
              {!a.is_returnable_buffer && (
                <View style={styles.posBadge}>
                  <Text style={styles.posText}>#{a.delivery_position}</Text>
                </View>
              )}
              <Text style={styles.boxes}>{a.boxes || '—'} cajas</Text>
            </View>
          </View>
        )}
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
  pallet: {
    width: 36, height: 36, borderRadius: 8,
    backgroundColor: COLORS.dark,
    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  palletText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  info: { flex: 1 },
  zone: { fontSize: 11, color: COLORS.muted },
  clientName: { fontSize: 13, fontWeight: '600', color: COLORS.dark },
  retornBadge: {
    backgroundColor: '#f3f4f6',
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 2,
    alignSelf: 'flex-start',
  },
  retornText: { fontSize: 11, color: COLORS.muted, fontWeight: '600' },
  right: { alignItems: 'flex-end', flexShrink: 0 },
  posBadge: {
    backgroundColor: '#dbeafe',
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginBottom: 2,
  },
  posText: { fontSize: 10, color: '#1d4ed8', fontWeight: '700' },
  boxes: { fontSize: 11, color: COLORS.muted },
  separator: { height: 10 },
})
