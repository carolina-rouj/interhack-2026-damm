import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native'
import { COLORS } from '../constants'

export default function ControlPanel({
  seed, setSeed, nClients, setNClients, startTime, setStartTime,
  scenario, loading, error, handleGenerate, handleOptimize,
}) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Configuración</Text>

      <View style={styles.row}>
        <Text style={styles.label}>Semilla aleatoria</Text>
        <TextInput
          style={styles.input}
          value={String(seed)}
          keyboardType="numeric"
          onChangeText={v => setSeed(Number(v) || 0)}
        />
      </View>

      <View style={styles.row}>
        <Text style={styles.label}>Número de clientes</Text>
        <TextInput
          style={styles.input}
          value={String(nClients)}
          keyboardType="numeric"
          onChangeText={v => setNClients(Number(v) || 0)}
        />
      </View>

      <View style={styles.row}>
        <Text style={styles.label}>Hora inicio ruta</Text>
        <TextInput
          style={styles.input}
          value={startTime}
          placeholder="08:00"
          onChangeText={setStartTime}
        />
      </View>

      {loading && <ActivityIndicator color={COLORS.red} style={{ marginBottom: 8 }} />}

      <TouchableOpacity style={styles.btnDark} onPress={handleGenerate} disabled={loading}>
        <Text style={styles.btnText}>Generar escenario</Text>
      </TouchableOpacity>

      {scenario && (
        <TouchableOpacity style={styles.btnRed} onPress={handleOptimize} disabled={loading}>
          <Text style={styles.btnText}>Optimizar ruta + carga</Text>
        </TouchableOpacity>
      )}

      {scenario && (
        <View style={styles.scenarioInfo}>
          <Text style={styles.scenarioTitle}>Escenario activo</Text>
          <Text style={styles.scenarioText}>Zona: {scenario.zone.name}</Text>
          <Text style={styles.scenarioText}>Depósito: {scenario.zone.depot.name}</Text>
          <Text style={styles.scenarioText}>Clientes: {scenario.clients.length}</Text>
        </View>
      )}

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  title: { fontSize: 15, fontWeight: '700', color: COLORS.dark, marginBottom: 12 },
  row: { marginBottom: 10 },
  label: { fontSize: 12, color: COLORS.muted, marginBottom: 4 },
  input: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 14,
    color: COLORS.dark,
  },
  btnDark: {
    backgroundColor: COLORS.dark,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    marginBottom: 8,
  },
  btnRed: {
    backgroundColor: COLORS.red,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    marginBottom: 8,
  },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  scenarioInfo: {
    backgroundColor: COLORS.bg,
    borderRadius: 8,
    padding: 10,
    marginTop: 4,
  },
  scenarioTitle: { fontSize: 12, fontWeight: '700', color: COLORS.dark, marginBottom: 4 },
  scenarioText: { fontSize: 12, color: COLORS.muted },
  errorBox: {
    backgroundColor: '#fef2f2',
    borderRadius: 8,
    padding: 10,
    marginTop: 8,
  },
  errorText: { color: '#b91c1c', fontSize: 12 },
})
