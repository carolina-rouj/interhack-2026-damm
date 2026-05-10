import React, { useState, useRef } from 'react'
import { View, Text, StyleSheet, Animated, TouchableOpacity, Dimensions, ScrollView } from 'react-native'
import TruckGrid3D from '../components/TruckGrid3D'
import { COLORS, MOCK_STOPS, TRUCK_CONFIGS, PALETTE } from '../constants'

const SCREEN_HEIGHT = Dimensions.get('window').height;

const generateFullTruckMock = (stops, truckType = '6pal') => {
  const cfg = TRUCK_CONFIGS[truckType] || TRUCK_CONFIGS['6pal'];
  const items = [];
  const sliceSize = (cfg.zHalf * 2) / stops.length;
  const zMin = -cfg.zHalf;

  stops.forEach((stop, i) => {
    const zStart = zMin + i * sliceSize;
    const zEnd = zStart + sliceSize - 0.1;
    for (let x = -cfg.xRange; x <= cfg.xRange; x += 0.4) {
      for (let y = -0.7; y <= 0.4; y += 0.3) {
        for (let z = zStart; z <= zEnd; z += 0.4) {
          const isBarrel = Math.random() > 0.75;
          items.push({
            id: `pkg_${stop.client.client_id}_${x.toFixed(1)}_${y.toFixed(1)}_${z.toFixed(1)}`,
            client_id: stop.client.client_id,
            tipo: isBarrel ? 'barril' : 'caja',
            x: x + (Math.random() * 0.02),
            y: y + (isBarrel ? 0.1 : 0),
            z: z + (Math.random() * 0.02),
          });
        }
      }
    }
  });

  return {
    route: { stops },
    load_plan: { items, truck_type: truckType },
    returnables_plan: { per_client: { m1: 6, m3: 12, m5: 4 } },
  };
};

const MOCK_RESULT = generateFullTruckMock(MOCK_STOPS, '6pal');

function PickingRow({ stop, globalIndex, isDelivered, counts, returnables }) {
  const cajas = counts?.cajas || 0
  const barriles = counts?.barriles || 0
  const countParts = []
  if (cajas > 0) countParts.push(`${cajas} caja${cajas !== 1 ? 's' : ''}`)
  if (barriles > 0) countParts.push(`${barriles} barril${barriles !== 1 ? 'es' : ''}`)
  const countText = countParts.join(' · ') || '—'

  return (
    <View style={[pStyles.row, isDelivered && pStyles.rowDone]}>
      <View style={[pStyles.circle, { backgroundColor: PALETTE[globalIndex % PALETTE.length] }]}>
        <Text style={pStyles.circleText}>{globalIndex + 1}</Text>
      </View>
      <View style={pStyles.info}>
        <Text style={[pStyles.name, isDelivered && pStyles.nameDone]} numberOfLines={1}>
          {stop.client.name}
        </Text>
        <Text style={pStyles.count}>{countText}</Text>
      </View>
      {isDelivered ? (
        <View style={pStyles.badgeDone}>
          <Text style={pStyles.badgeDoneText}>{returnables > 0 ? `↩ ${returnables}` : '✓'}</Text>
        </View>
      ) : (
        <View style={pStyles.badgePending}>
          <Text style={pStyles.badgePendingText}>Pendiente</Text>
        </View>
      )}
    </View>
  )
}

export default function LoadScreen({ result, deliveredIds }) {
  const displayResult = result || MOCK_RESULT;
  const stops = displayResult.route.stops || [];
  const ids = deliveredIds || new Set()
  const loadPlan = displayResult.load_plan
  const retornablesPerClient = displayResult.returnables_plan?.per_client || {}

  const itemCounts = {}
  ;(loadPlan?.items || []).forEach(item => {
    if (!itemCounts[item.client_id]) itemCounts[item.client_id] = { cajas: 0, barriles: 0 }
    item.tipo === 'barril' ? itemCounts[item.client_id].barriles++ : itemCounts[item.client_id].cajas++
  })

  const pendingStops = stops.filter(s => !ids.has(s.client.client_id))
  const deliveredStops = stops.filter(s => ids.has(s.client.client_id))

  const [isExpanded, setIsExpanded] = useState(false);
  const sheetHeight = useRef(new Animated.Value(70)).current;

  const toggleSheet = () => {
    const toValue = isExpanded ? 70 : SCREEN_HEIGHT * 0.55;
    Animated.spring(sheetHeight, { toValue, friction: 8, useNativeDriver: false }).start();
    setIsExpanded(!isExpanded);
  };

  return (
    <View style={styles.screen}>
      <View style={styles.mapContainer}>
        <TruckGrid3D
          loadPlan={loadPlan}
          stops={stops}
          deliveredIds={ids}
          truckType={loadPlan?.truck_type || '6pal'}
        />
      </View>

      <Animated.View style={[styles.bottomSheet, { height: sheetHeight }]}>
        <TouchableOpacity style={styles.sheetHeader} onPress={toggleSheet} activeOpacity={0.9}>
          <View style={styles.dragHandle} />
          <Text style={styles.sheetTitle}>
            {isExpanded ? 'Ocultar lista de picking' : 'Ver lista de picking'}
          </Text>
        </TouchableOpacity>

        {isExpanded && (
          <ScrollView style={styles.sheetContent} showsVerticalScrollIndicator={false}>
            {pendingStops.length > 0 && (
              <>
                <Text style={pStyles.sectionHeader}>
                  Por entregar · {pendingStops.length}
                </Text>
                {pendingStops.map(stop => {
                  const gi = stops.indexOf(stop)
                  return (
                    <PickingRow
                      key={stop.client.client_id}
                      stop={stop}
                      globalIndex={gi}
                      isDelivered={false}
                      counts={itemCounts[stop.client.client_id]}
                      returnables={0}
                    />
                  )
                })}
              </>
            )}

            {deliveredStops.length > 0 && (
              <>
                <Text style={[pStyles.sectionHeader, { marginTop: 16 }]}>
                  Entregado · {deliveredStops.length}
                </Text>
                {deliveredStops.map(stop => {
                  const gi = stops.indexOf(stop)
                  const ret = retornablesPerClient[stop.client.client_id] || 0
                  return (
                    <PickingRow
                      key={stop.client.client_id}
                      stop={stop}
                      globalIndex={gi}
                      isDelivered={true}
                      counts={itemCounts[stop.client.client_id]}
                      returnables={ret}
                    />
                  )
                })}
              </>
            )}
            <View style={{ height: 16 }} />
          </ScrollView>
        )}
      </Animated.View>
    </View>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0f172a' },
  mapContainer: { flex: 1 },
  bottomSheet: { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: '#ffffff', borderTopLeftRadius: 24, borderTopRightRadius: 24, elevation: 15 },
  sheetHeader: { height: 70, alignItems: 'center', justifyContent: 'center', borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  dragHandle: { width: 40, height: 5, backgroundColor: '#cbd5e1', borderRadius: 3, marginBottom: 8 },
  sheetTitle: { fontSize: 14, fontWeight: '700', color: COLORS.dark },
  sheetContent: { flex: 1, paddingHorizontal: 14 },
})

const pStyles = StyleSheet.create({
  sectionHeader: {
    fontSize: 11, fontWeight: '700', color: '#94a3b8',
    letterSpacing: 0.8, textTransform: 'uppercase',
    marginTop: 12, marginBottom: 6, marginLeft: 2,
  },
  row: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#f8fafc', borderRadius: 12,
    padding: 10, marginBottom: 6, gap: 10,
  },
  rowDone: { opacity: 0.55 },
  circle: {
    width: 30, height: 30, borderRadius: 15,
    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  circleText: { color: '#fff', fontWeight: '800', fontSize: 12 },
  info: { flex: 1 },
  name: { fontSize: 13, fontWeight: '600', color: '#0f172a' },
  nameDone: { color: '#94a3b8' },
  count: { fontSize: 11, color: '#64748b', marginTop: 2 },
  badgeDone: {
    backgroundColor: '#dcfce7', paddingHorizontal: 10, paddingVertical: 4,
    borderRadius: 999, flexShrink: 0,
  },
  badgeDoneText: { fontSize: 12, fontWeight: '700', color: '#16a34a' },
  badgePending: {
    backgroundColor: '#fef9c3', paddingHorizontal: 10, paddingVertical: 4,
    borderRadius: 999, flexShrink: 0,
  },
  badgePendingText: { fontSize: 12, fontWeight: '700', color: '#a16207' },
})