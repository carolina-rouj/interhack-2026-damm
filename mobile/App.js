import { useState, useEffect } from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { Text } from 'react-native'
import { StatusBar } from 'expo-status-bar'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { transformRouteJson } from './src/utils/transform'
import routeData from './src/data/route.json'
import RouteScreen from './src/screens/RouteScreen'
import LoadScreen from './src/screens/LoadScreen'
import { COLORS } from './src/constants'
import { Package, Map } from 'lucide-react-native'

const Tab = createBottomTabNavigator()

export default function App() {
  const [scenario, setScenario] = useState(null)
  const [result, setResult] = useState(null)
  const [deliveredIds, setDeliveredIds] = useState(new Set())

  useEffect(() => {
    const transformed = transformRouteJson(routeData)
    setScenario(transformed.scenario)
    setResult(transformed.result)
  }, [])

  useEffect(() => { setDeliveredIds(new Set()) }, [result])

  function toggleDelivered(clientId) {
    setDeliveredIds(prev => {
      const next = new Set(prev)
      next.has(clientId) ? next.delete(clientId) : next.add(clientId)
      return next
    })
  }

  const sharedProps = {
    scenario, result,
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
