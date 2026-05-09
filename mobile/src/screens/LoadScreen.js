import React, { useState, useRef } from 'react'
import { View, Text, StyleSheet, Animated, TouchableOpacity, Dimensions } from 'react-native'
import TruckGrid3D from '../components/TruckGrid3D' 
import { COLORS } from '../constants'

const SCREEN_HEIGHT = Dimensions.get('window').height;

// SIMULADOR DEL BACKEND: Genera un camión LLENO optimizado al máximo
const generateFullTruckMock = () => {
  const items = [];
  const stops = [
    { client: { client_id: "9100702970", name: "1. KAPHIY BRUNCH" }, zStart: 0.8, zEnd: 2.2 },
    { client: { client_id: "9100733214", name: "2. BAR VAGON 66" }, zStart: -0.8, zEnd: 0.6 },
    { client: { client_id: "104047", name: "3. VIENA GRANOLLERS" }, zStart: -2.2, zEnd: -1.0 }
  ];

  stops.forEach((stop) => {
    // Bucle para rellenar el espacio volumétrico del camión (X: Ancho, Y: Alto, Z: Largo)
    for (let x = -0.8; x <= 0.8; x += 0.4) {
      for (let y = -0.7; y <= 0.4; y += 0.3) {
        for (let z = stop.zStart; z <= stop.zEnd; z += 0.4) {
          
          // Mezclamos un 25% de barriles y un 75% de cajas aleatoriamente
          const isBarrel = Math.random() > 0.75;
          
          items.push({
            id: `pkg_${x}_${y}_${z}`,
            client_id: stop.client.client_id,
            tipo: isBarrel ? 'barril' : 'caja',
            x: x + (Math.random() * 0.02), // Pequeña imperfección realista
            y: y + (isBarrel ? 0.1 : 0),   // Ajuste de altura para el barril
            z: z + (Math.random() * 0.02),
          });
        }
      }
    }
  });

  return { route: { stops }, load_plan: { items } };
};

const MOCK_RESULT = generateFullTruckMock();

export default function LoadScreen({ result }) {
  const displayResult = result || MOCK_RESULT;
  const stops = displayResult.route.stops || [];

  const [isExpanded, setIsExpanded] = useState(false);
  const sheetHeight = useRef(new Animated.Value(70)).current; 

  const toggleSheet = () => {
    const toValue = isExpanded ? 70 : SCREEN_HEIGHT * 0.4; 
    Animated.spring(sheetHeight, { toValue, friction: 8, useNativeDriver: false }).start();
    setIsExpanded(!isExpanded);
  };

  return (
    <View style={styles.screen}>
      <View style={styles.mapContainer}>
        {/* Pasamos los 150+ ítems generados al visor */}
        <TruckGrid3D loadPlan={displayResult.load_plan} stops={stops} />
      </View>

      <Animated.View style={[styles.bottomSheet, { height: sheetHeight }]}>
        <TouchableOpacity style={styles.sheetHeader} onPress={toggleSheet} activeOpacity={0.9}>
          <View style={styles.dragHandle} />
          <Text style={styles.sheetTitle}>
            {isExpanded ? "Ocultar tabla de picking" : "Ver lista manual de picking"}
          </Text>
        </TouchableOpacity>
        
        {isExpanded && (
          <View style={styles.sheetContent}>
            <Text style={{color: COLORS.muted}}>
              Aquí irá la tabla de texto si el repartidor prefiere leer en lugar del 3D.
            </Text>
          </View>
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
  sheetContent: { flex: 1, padding: 16 }
});