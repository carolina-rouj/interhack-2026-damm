import { useState, useEffect } from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { Text } from 'react-native'
import { StatusBar } from 'expo-status-bar'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { getZones, solveRoute } from './src/api'
import { transformSolveResponse } from './src/utils/transform'
import RouteScreen from './src/screens/RouteScreen'
import LoadScreen from './src/screens/LoadScreen'
import { COLORS } from './src/constants'
import { Package, Map } from 'lucide-react-native'

const Tab = createBottomTabNavigator()

const DEFAULT_ZONA = 'granollers-center-01'

export default function App() {
  const [zonaId, setZonaId] = useState(DEFAULT_ZONA)
  const [zones, setZones] = useState([])
  const [scenario, setScenario] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [deliveredIds, setDeliveredIds] = useState(new Set())

  useEffect(() => {
    getZones()
      .then(data => setZones(data.zonas || []))
      .catch(() => {})
  }, [])

  useEffect(() => { setDeliveredIds(new Set()) }, [result])

  function toggleDelivered(clientId) {
    setDeliveredIds(prev => {
      const next = new Set(prev)
      next.has(clientId) ? next.delete(clientId) : next.add(clientId)
      return next
    })
  }

  async function handleSolve() {
    setLoading(true)
    setError(null)
    setResult(null)
    setScenario(null)
    try {
      const data = await solveRoute(zonaId)
      const transformed = transformSolveResponse(data)
      setScenario(transformed.scenario)
      setResult(transformed.result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const sharedProps = {
    zonaId, setZonaId, zones,
    scenario, result, loading, error, handleSolve,
    deliveredIds, toggleDelivered,
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <Tab.Navigator
          screenOptions={{
            tabBarActiveTintColor: COLORS.red,
            tabBarInactiveTintColor: '#94a3b8',
            tabBarStyle: {
              backgroundColor: '#fff',
              borderTopWidth: 0,
              shadowColor: '#000',
              shadowOpacity: 0.08,
              shadowRadius: 16,
              shadowOffset: { width: 0, height: -4 },
              elevation: 12,
            },
            tabBarLabelStyle: { fontSize: 11, fontWeight: '600', letterSpacing: 0.3 },
            headerStyle: { backgroundColor: COLORS.red },
            headerTintColor: '#fff',
            headerTitleStyle: { fontWeight: '700', fontSize: 16, letterSpacing: 0.3 },
            headerRight: () => (
              <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11, marginRight: 16, fontWeight: '500', letterSpacing: 0.5 }}>
                DAMM
              </Text>
            ),
          }}
        >
          <Tab.Screen
            name="Ruta"
            options={{ tabBarIcon: ({ color }) => <Map size={22} color={color} /> }}
          >
            {() => <RouteScreen {...sharedProps} />}
          </Tab.Screen>

          <Tab.Screen
            name="Carga"
            options={{ tabBarIcon: ({ color }) => <Package size={22} color={color} /> }}
          >
            {() => <LoadScreen {...sharedProps} />}
          </Tab.Screen>
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  )
}
