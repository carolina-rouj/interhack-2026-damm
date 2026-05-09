import { View, Text, ScrollView, StyleSheet } from 'react-native'
import TruckGrid from '../components/TruckGrid'
import LoadTable from '../components/LoadTable'
import { COLORS } from '../constants'

export default function LoadScreen({ result }) {
  const stops = result?.route?.stops || []

  if (!result) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyIcon}>📦</Text>
        <Text style={styles.emptyTitle}>Sin datos de carga</Text>
        <Text style={styles.emptyText}>
          Ve a la pestaña Ruta, genera un escenario y optimiza para ver el plan de carga del camión.
        </Text>
      </View>
    )
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <TruckGrid loadPlan={result.load_plan} stops={stops} />
      <LoadTable loadPlan={result.load_plan} />
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.bg },
  content: { padding: 12 },
  emptyContainer: {
    flex: 1,
    backgroundColor: COLORS.bg,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  emptyIcon: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: COLORS.dark, marginBottom: 8 },
  emptyText: { fontSize: 14, color: COLORS.muted, textAlign: 'center', lineHeight: 20 },
})
