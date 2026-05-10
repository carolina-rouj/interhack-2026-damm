import { Modal, View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { X, FileDown } from 'lucide-react-native'
import { buildReportData } from '../utils/reportGenerator'

export default function ReportPreviewModal({ visible, result, onClose, onDownload, downloading }) {
  if (!result) return null
  const { stops, routeId, zonaId, truckLabel, today, grandCajas, grandBarriles, skuMap } = buildReportData(result)

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <View style={s.container}>

        {/* Header */}
        <View style={s.header}>
          <View>
            <Text style={s.headerTitle}>Informe de Ruta</Text>
            <Text style={s.headerSub}>Damm Smart Truck</Text>
          </View>
          <TouchableOpacity onPress={onClose} style={s.closeBtn} hitSlop={12}>
            <X size={20} color="rgba(255,255,255,0.9)" />
          </TouchableOpacity>
        </View>

        <ScrollView style={s.scroll} contentContainerStyle={s.scrollContent} showsVerticalScrollIndicator={false}>

          {/* Route meta */}
          {(routeId || zonaId) && (
            <View style={s.metaRow}>
              {routeId && <Text style={s.metaText}>Ruta: <Text style={s.metaBold}>{routeId}</Text></Text>}
              {zonaId && <Text style={s.metaText}>Zona: <Text style={s.metaBold}>{zonaId}</Text></Text>}
              <Text style={s.metaText}>Fecha: <Text style={s.metaBold}>{today}</Text></Text>
            </View>
          )}

          {/* Summary stats */}
          <View style={s.statsRow}>
            <View style={s.statBox}>
              <Text style={s.statLabel}>Paradas</Text>
              <Text style={s.statValue}>{stops.length}</Text>
            </View>
            <View style={s.statBox}>
              <Text style={s.statLabel}>Cajas</Text>
              <Text style={s.statValue}>{grandCajas}</Text>
            </View>
            <View style={s.statBox}>
              <Text style={s.statLabel}>Barriles</Text>
              <Text style={s.statValue}>{grandBarriles}</Text>
            </View>
          </View>

          {/* SKU totals */}
          <Text style={s.sectionTitle}>Productos por SKU</Text>
          <View style={s.table}>
            <View style={[s.tableRow, s.tableHead]}>
              <Text style={[s.thCell, { flex: 1 }]}>SKU</Text>
              <Text style={[s.thCell, { flex: 3 }]}>Producto</Text>
              <Text style={[s.thCell, { flex: 1.2, textAlign: 'center' }]}>Tipo</Text>
              <Text style={[s.thCell, { flex: 1, textAlign: 'right' }]}>Uds.</Text>
            </View>
            {Object.entries(skuMap).map(([sku, d]) => (
              <View key={sku} style={s.tableRow}>
                <Text style={[s.tdCell, { flex: 1, fontWeight: '700' }]}>{sku}</Text>
                <Text style={[s.tdCell, { flex: 3 }]}>{d.nombre}</Text>
                <View style={[{ flex: 1.2, alignItems: 'center', justifyContent: 'center' }]}>
                  <View style={d.tipo_envase === 'barril' ? s.badgeBarril : s.badgeCaja}>
                    <Text style={d.tipo_envase === 'barril' ? s.badgeBarrilText : s.badgeCajaText}>
                      {d.tipo_envase === 'barril' ? 'Barril' : 'Caja'}
                    </Text>
                  </View>
                </View>
                <Text style={[s.tdCell, { flex: 1, textAlign: 'right', fontWeight: '700' }]}>{d.total}</Text>
              </View>
            ))}
          </View>

          {/* Per-stop detail */}
          <Text style={[s.sectionTitle, { marginTop: 20 }]}>Detalle por parada</Text>
          {stops.map((stop, i) => {
            const productos = stop.client.productos ?? []
            return (
              <View key={stop.client.client_id} style={s.stopCard}>
                <View style={s.stopHeader}>
                  <View style={s.stopBadge}>
                    <Text style={s.stopBadgeText}>{i + 1}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={s.stopName}>{stop.client.name}</Text>
                    <Text style={s.stopMeta}>Llegada: {stop.arrival_time} · {stop._total_boxes ?? 0} cajas</Text>
                  </View>
                </View>
                {productos.map((p, j) => (
                  <View key={j} style={s.productRow}>
                    <Text style={s.productName}>{p.nombre}</Text>
                    <Text style={s.productQty}>
                      {p.cantidad_cajas} {p.tipo_envase === 'barril' ? 'barriles' : 'cajas'}
                    </Text>
                  </View>
                ))}
              </View>
            )
          })}

          <Text style={s.footer}>Generado el {today} · {truckLabel}</Text>
        </ScrollView>

        {/* Bottom action bar */}
        <View style={s.bottomBar}>
          <TouchableOpacity style={s.closeAction} onPress={onClose} activeOpacity={0.8}>
            <Text style={s.closeActionText}>Cerrar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.downloadAction} onPress={onDownload} disabled={downloading} activeOpacity={0.85}>
            {downloading
              ? <ActivityIndicator size="small" color="#fff" />
              : <FileDown size={16} color="#fff" />
            }
            <Text style={s.downloadActionText}>{downloading ? 'Generando...' : 'Descargar PDF'}</Text>
          </TouchableOpacity>
        </View>

      </View>
    </Modal>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },

  header: {
    backgroundColor: '#c00000',
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 20, paddingTop: 20, paddingBottom: 18,
  },
  headerTitle: { fontSize: 18, fontWeight: '800', color: '#fff', letterSpacing: -0.3 },
  headerSub: { fontSize: 12, color: 'rgba(255,255,255,0.75)', marginTop: 2 },
  closeBtn: { padding: 4 },

  scroll: { flex: 1 },
  scrollContent: { padding: 16, paddingBottom: 32 },

  metaRow: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 12, gap: 4, borderWidth: 1, borderColor: '#e2e8f0' },
  metaText: { fontSize: 12, color: '#64748b' },
  metaBold: { fontWeight: '700', color: '#0f172a' },

  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 20 },
  statBox: { flex: 1, backgroundColor: '#fff', borderRadius: 10, padding: 14, alignItems: 'center', borderWidth: 1, borderColor: '#e2e8f0' },
  statLabel: { fontSize: 10, fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 },
  statValue: { fontSize: 24, fontWeight: '800', color: '#0f172a' },

  sectionTitle: { fontSize: 13, fontWeight: '700', color: '#0f172a', marginBottom: 8, paddingBottom: 6, borderBottomWidth: 2, borderBottomColor: '#e2e8f0' },

  table: { backgroundColor: '#fff', borderRadius: 10, overflow: 'hidden', borderWidth: 1, borderColor: '#e2e8f0' },
  tableRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 9, paddingHorizontal: 12, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  tableHead: { backgroundColor: '#f1f5f9' },
  thCell: { fontSize: 10, fontWeight: '700', color: '#475569', textTransform: 'uppercase', letterSpacing: 0.4 },
  tdCell: { fontSize: 12, color: '#0f172a' },
  badgeCaja: { backgroundColor: '#dbeafe', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  badgeCajaText: { fontSize: 10, fontWeight: '700', color: '#1e40af' },
  badgeBarril: { backgroundColor: '#fef3c7', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  badgeBarrilText: { fontSize: 10, fontWeight: '700', color: '#92400e' },

  stopCard: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#e2e8f0' },
  stopHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 8 },
  stopBadge: { width: 28, height: 28, borderRadius: 14, backgroundColor: '#c00000', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 },
  stopBadgeText: { fontSize: 12, fontWeight: '800', color: '#fff' },
  stopName: { fontSize: 14, fontWeight: '700', color: '#0f172a' },
  stopMeta: { fontSize: 11, color: '#64748b', marginTop: 2 },
  productRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, borderTopWidth: 1, borderTopColor: '#f1f5f9' },
  productName: { fontSize: 12, color: '#475569', flex: 1 },
  productQty: { fontSize: 12, fontWeight: '600', color: '#0f172a' },

  footer: { fontSize: 11, color: '#94a3b8', textAlign: 'center', marginTop: 20 },

  bottomBar: {
    flexDirection: 'row', gap: 10,
    padding: 16, paddingBottom: 32,
    backgroundColor: '#fff',
    borderTopWidth: 1, borderTopColor: '#e2e8f0',
  },
  closeAction: {
    flex: 1, borderRadius: 14, paddingVertical: 14,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: '#f1f5f9',
  },
  closeActionText: { fontSize: 15, fontWeight: '700', color: '#475569' },
  downloadAction: {
    flex: 2, borderRadius: 14, paddingVertical: 14,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: '#3b82f6',
  },
  downloadActionText: { fontSize: 15, fontWeight: '700', color: '#fff' },
})
