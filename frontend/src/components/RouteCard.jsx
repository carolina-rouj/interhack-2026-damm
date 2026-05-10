import { useState, useEffect } from 'react';
import { Van, Truck, Clock } from 'lucide-react';

const TRUCK_ICONS  = { furgoneta: Van, mediano: Truck, grande: Truck };
const TRUCK_LABELS = { furgoneta: 'Furgoneta (Van)', mediano: 'Camión Mediano', grande: 'Camión Grande' };

function fmtTime(minutes) {
  if (minutes == null) return '--:--';
  const h = String(Math.floor(minutes / 60)).padStart(2, '0');
  const m = String(minutes % 60).padStart(2, '0');
  return `${h}:${m}`;
}

export default function RouteCard({ routeObj, index, animationOffset = 0 }) {
  const route = routeObj.route;
  const [revealed, setRevealed] = useState([]);

  useEffect(() => {
    const timers = (route.paradas ?? []).map((_, si) =>
      setTimeout(
        () => setRevealed(prev => [...prev, si]),
        animationOffset + si * 620,
      )
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  const Icon  = TRUCK_ICONS[route.tipo_camion]  ?? Truck;
  const label = TRUCK_LABELS[route.tipo_camion] ?? route.tipo_camion;

  return (
    <div className="route-card">
      <div className="route-header">
        <span className="truck-icon"><Icon size={24} strokeWidth={1.5} /></span>
        <span className="route-title">Route {index} — {label}</span>
        <span className="badge highlight">
          {route.num_palets} pallet{route.num_palets !== 1 ? 's' : ''}
        </span>
        <span className="badge">{(route.paradas ?? []).length} stops</span>
      </div>

      <div className="stops-list">
        {(route.paradas ?? []).map((parada, si) => (
          <div
            key={si}
            className={`stop-item${revealed.includes(si) ? ' revealed' : ''}`}
          >
            <span className="stop-num">{si + 1}</span>
            <div className="stop-body">
              <span className="stop-time">
                <Clock size={12} strokeWidth={2} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                {fmtTime(parada.llegada_min)}
              </span>
              <ul className="clients-list">
                {(parada.clientes ?? []).map((c, ci) => (
                  <li key={ci} className="client-row">
                    <span className="client-name">{c.nombre}</span>
                    <div className="chips">
                      {(c.productos ?? []).map((p, pi) => (
                        <span
                          key={pi}
                          className={`chip${p.tipo_envase === 'barril' ? ' barrel' : ''}`}
                        >
                          {p.nombre.split(' ').slice(0, 2).join(' ')} ×{p.cantidad_cajas}
                        </span>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
