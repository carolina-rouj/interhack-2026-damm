import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Canvas } from '@react-three/fiber/native';
import { OrbitControls } from '@react-three/drei/native';
import { COLORS, PALETTE } from '../constants';

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

// Estructura física del camión de reparto
function TruckStructure() {
  return (
    <group>
      {/* Contenedor translúcido (más estrecho y largo) */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[2.2, 1.8, 5.2]} />
        <meshBasicMaterial color="#94a3b8" wireframe={true} opacity={0.3} transparent />
      </mesh>
      {/* Suelo sólido del camión para dar referencia espacial */}
      <mesh position={[0, -0.9, 0]}>
        <boxGeometry args={[2.2, 0.05, 5.2]} />
        <meshStandardMaterial color="#475569" />
      </mesh>
    </group>
  );
}

export default function TruckGrid3D({ loadPlan, stops }) {
  const [currentStopIndex, setCurrentStopIndex] = useState(0);

  if (!loadPlan || !stops) return null;

  const clientColorMap = {};
  stops.forEach((stop, i) => {
    clientColorMap[stop.client.client_id] = PALETTE[i % PALETTE.length];
  });

  const currentStop = stops[currentStopIndex];
  const currentClientId = currentStop?.client?.client_id;

  return (
    <View style={styles.container}>
      <View style={styles.overlayControls}>
        <TouchableOpacity 
          style={[styles.btn, currentStopIndex === 0 && styles.btnDisabled]}
          onPress={() => setCurrentStopIndex(Math.max(0, currentStopIndex - 1))}
        >
          <Text style={styles.btnText}>Anterior</Text>
        </TouchableOpacity>
        
        <View style={styles.statusBox}>
          <Text style={styles.statusText}>Pickup - Parada {currentStopIndex + 1}</Text>
          <Text style={styles.clientName} numberOfLines={1}>{currentStop?.client?.name}</Text>
        </View>

        <TouchableOpacity 
          style={[styles.btn, currentStopIndex === stops.length - 1 && styles.btnDisabled]}
          onPress={() => setCurrentStopIndex(Math.min(stops.length - 1, currentStopIndex + 1))}
        >
          <Text style={styles.btnText}>Siguiente</Text>
        </TouchableOpacity>
      </View>

      <Canvas camera={{ position: [4, 3, 6], fov: 45 }}>
        {/* Controles a prueba de fallos: SOLO ROTACIÓN */}
        <OrbitControls 
          enableZoom={false} 
          enablePan={false} 
          enableRotate={true}
          enableDamping={true}
          dampingFactor={0.05}
        />
        
        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 10, 5]} intensity={1} />
        
        <TruckStructure />
        
        {/* Renderizado de cientos de ítems individuales enviados por el backend */}
        {loadPlan.items.map((item, index) => {
          const color = clientColorMap[item.client_id] || '#e5e7eb';
          const isHighlighted = item.client_id === currentClientId;
          
          // Lógica LIFO
          const stopIndexOfThisItem = stops.findIndex(s => s.client.client_id === item.client_id);
          const isVisible = stopIndexOfThisItem >= currentStopIndex;

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
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.95)', padding: 12, borderRadius: 12,
    shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 10, elevation: 5,
  },
  btn: { backgroundColor: COLORS.red, paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8 },
  btnDisabled: { backgroundColor: COLORS.muted },
  btnText: { color: '#fff', fontWeight: 'bold', fontSize: 13 },
  statusBox: { flex: 1, alignItems: 'center', paddingHorizontal: 8 },
  statusText: { fontSize: 11, color: COLORS.red, fontWeight: '700', marginBottom: 2 },
  clientName: { fontSize: 13, fontWeight: '800', color: COLORS.dark },
});