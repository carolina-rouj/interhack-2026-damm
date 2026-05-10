import React, { useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { Canvas } from '@react-three/fiber/native';
import { OrbitControls } from '@react-three/drei/native';
import { COLORS, PALETTE, TRUCK_CONFIGS } from '../constants';

// Componente que renderiza una CAJA o un BARRIL individual
function Item3D({ position, tipo, color, isVisible, isHighlighted }) {
  if (!isVisible) return null;

  return (
    <mesh position={position}>
      {tipo === 'barril' ? (
        // Barril: Radio arriba, radio abajo, altura, segmentos
        <cylinderGeometry args={[0.2, 0.2, 0.5, 16]} /> 
      ) : (
        // Caja: Ancho, alto, profundidad
        <boxGeometry args={[0.35, 0.25, 0.35]} /> 
      )}
      <meshStandardMaterial 
        color={color} 
        emissive={isHighlighted ? color : '#000000'}
        emissiveIntensity={isHighlighted ? 1.2 : 0}
        opacity={isHighlighted ? 1 : 0.4} 
        transparent={true}
        roughness={0.8}
      />
    </mesh>
  );
}

function TruckStructure({ config }) {
  return (
    <group>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[config.boxW, config.boxH, config.boxL]} />
        <meshBasicMaterial color="#94a3b8" wireframe={true} opacity={0.3} transparent />
      </mesh>
      <mesh position={[0, -(config.boxH / 2 - 0.025), 0]}>
        <boxGeometry args={[config.boxW, 0.05, config.boxL]} />
        <meshStandardMaterial color="#475569" />
      </mesh>
    </group>
  );
}

export default function TruckGrid3D({ loadPlan, stops, deliveredIds, truckType = '6pal' }) {
  const config = TRUCK_CONFIGS[truckType] || TRUCK_CONFIGS['6pal'];
  const [ready, setReady] = useState(false);
  if (!loadPlan || !stops) return null;

  const clientColorMap = {};
  stops.forEach((stop, i) => {
    clientColorMap[stop.client.client_id] = PALETTE[i % PALETTE.length];
  });

  const currentStop = stops.find(s => !deliveredIds.has(s.client.client_id));
  const currentClientId = currentStop?.client?.client_id;
  const currentStopNumber = stops.indexOf(currentStop) + 1;
  const allDelivered = !currentStop;

  return (
    <View style={styles.container}>
      <View style={styles.overlayControls}>
        <View style={styles.statusBox}>
          {allDelivered ? (
            <Text style={styles.statusText}>Ruta completada</Text>
          ) : (
            <>
              <Text style={styles.statusText}>Próxima entrega · Parada {currentStopNumber}</Text>
              <Text style={styles.clientName} numberOfLines={1}>{currentStop?.client?.name}</Text>
            </>
          )}
        </View>
      </View>

      {!ready && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color={COLORS.red} />
          <Text style={styles.loadingText}>Cargando camión...</Text>
        </View>
      )}

      <Canvas key={truckType} camera={{ position: config.camera, fov: 45 }} onCreated={() => setReady(true)}>
        <OrbitControls
          enableZoom={false}
          enablePan={false}
          enableRotate={true}
          enableDamping={true}
          dampingFactor={0.05}
        />

        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 10, 5]} intensity={1} />

        <TruckStructure config={config} />

        {loadPlan.items.map((item) => {
          const color = clientColorMap[item.client_id] || '#e5e7eb';
          const isVisible = !deliveredIds.has(item.client_id);
          const isHighlighted = item.client_id === currentClientId;

          return (
            <Item3D
              key={item.id}
              position={[item.x, item.y, item.z]}
              tipo={item.tipo}
              color={color}
              isVisible={isVisible}
              isHighlighted={isHighlighted}
            />
          );
        })}
      </Canvas>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  overlayControls: {
    position: 'absolute', top: 20, left: 10, right: 10, zIndex: 10,
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.95)', padding: 12, borderRadius: 12,
    shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 10, elevation: 5,
  },
  statusBox: { alignItems: 'center' },
  statusText: { fontSize: 11, color: COLORS.red, fontWeight: '700', marginBottom: 2 },
  clientName: { fontSize: 13, fontWeight: '800', color: COLORS.dark },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 20,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: { color: '#94a3b8', fontSize: 13, fontWeight: '600' },
});