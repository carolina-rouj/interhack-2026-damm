export const COLORS = {
  red: '#c21515',
  dark: '#1a1a2e',
  bg: '#f4f6f8',
  card: '#ffffff',
  border: '#dde1e7',
  muted: '#6b7280',
  green: '#16a34a',
  orange: '#f59e0b',
  yellow: '#eab308',
}

export const PALETTE = [
  '#4e79a7','#f28e2b','#e15759','#76b7b2','#59a14f',
  '#edc948','#b07aa1','#ff9da7','#9c755f','#bab0ac',
  '#17becf','#aec7e8','#ffbb78','#98df8a','#ff9896',
  '#c5b0d5','#c49c94','#f7b6d2',
]

export const PRIORITY_COLORS = { 1: '#c21515', 2: '#f59e0b', 3: '#16a34a' }

// Dimensiones 3D por tipo de camión:
//   boxW/H/L  → tamaño del wireframe
//   xRange    → semiancho para colocar ítems (1 col = 0.4, 2 cols = 0.8)
//   zHalf     → semilargo para distribuir ítems (3 filas = 2.4, 4 filas = 3.2)
//   camera    → posición inicial de cámara
export const TRUCK_CONFIGS = {
  '3pal': { boxW: 1.2, boxH: 1.8, boxL: 5.2, xRange: 0.4, zHalf: 2.4, camera: [3, 3, 5] },
  '6pal': { boxW: 2.2, boxH: 1.8, boxL: 5.2, xRange: 0.8, zHalf: 2.4, camera: [4, 3, 6] },
  '8pal': { boxW: 2.2, boxH: 1.8, boxL: 6.8, xRange: 0.8, zHalf: 3.2, camera: [5, 4, 8] },
}

export const MOCK_DEPOT = { lat: 41.4065, lon: 2.1878, name: 'Fábrica Damm' }

export const MOCK_STOPS = [
  { client: { client_id: 'm1', name: 'Bar El Xampanyet',    lat: 41.3847, lon: 2.1834, priority: 1, time_window: { open_min: 480, close_min: 600 } }, arrival_time: '09:15', status: 'OK',                  wait_min: 0 },
  { client: { client_id: 'm2', name: 'Restaurant La Pepita', lat: 41.3901, lon: 2.1701, priority: 2, time_window: { open_min: 540, close_min: 660 } }, arrival_time: '09:45', status: 'OK',                  wait_min: 5 },
  { client: { client_id: 'm3', name: 'Cafetería Central',    lat: 41.4010, lon: 2.1750, priority: 3, time_window: { open_min: 600, close_min: 720 } }, arrival_time: '10:20', status: 'OK',                  wait_min: 0 },
  { client: { client_id: 'm4', name: 'Hotel Arts Bar',       lat: 41.3870, lon: 2.1970, priority: 1, time_window: { open_min: 480, close_min: 570 } }, arrival_time: '10:50', status: 'TIME_WINDOW_VIOLATED', wait_min: 0 },
  { client: { client_id: 'm5', name: 'Terraza Barceloneta',  lat: 41.3790, lon: 2.1900, priority: 2, time_window: { open_min: 660, close_min: 780 } }, arrival_time: '11:30', status: 'OK',                  wait_min: 0 },
]
