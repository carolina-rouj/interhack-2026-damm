import { useState } from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { Text } from 'react-native'
import { StatusBar } from 'expo-status-bar'
import { generateScenario, optimizeScenario } from './src/api'
import RouteScreen from './src/screens/RouteScreen'
import LoadScreen from './src/screens/LoadScreen'
import { COLORS } from './src/constants'
import { Package, Map } from 'lucide-react-native'


const Tab = createBottomTabNavigator()

export default function App() {
  const [seed, setSeed] = useState(42)
  const [nClients, setNClients] = useState(16)
  const [startTime, setStartTime] = useState('08:00')
  const [scenario, setScenario] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleGenerate() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await generateScenario(seed, nClients)
      setScenario(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleOptimize() {
    if (!scenario) return
    setLoading(true)
    setError(null)
    try {
      const data = await optimizeScenario(scenario.scenario_id, startTime)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const sharedProps = {
    seed, setSeed, nClients, setNClients, startTime, setStartTime,
    scenario, result, loading, error, handleGenerate, handleOptimize,
  }

  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={{
          tabBarActiveTintColor: COLORS.red,
          tabBarInactiveTintColor: COLORS.muted,
          tabBarStyle: { borderTopColor: COLORS.border },
          headerStyle: { backgroundColor: COLORS.dark },
          headerTintColor: '#fff',
          headerTitleStyle: { fontWeight: '700' },
          headerTitle: 'DAMM Smart Truck',
          headerRight: () => (
            <Text style={{ color: '#9ca3af', fontSize: 11, marginRight: 16 }}>
              Interhack BCN 2026
            </Text>
          ),
        }}
      >
        <Tab.Screen
          name="Ruta"
          options={{
            tabBarIcon: ({ color }) => <Map size={22} color={color} />,
          }}
        >
          {() => <RouteScreen {...sharedProps} />}
        </Tab.Screen>

        <Tab.Screen
          name="Carga"
          options={{
            tabBarIcon: ({ color }) => <Package size={22} color={color} />,
          }}
        >
          {() => <LoadScreen {...sharedProps} />}
        </Tab.Screen>
      </Tab.Navigator>
    </NavigationContainer>
  )
}
