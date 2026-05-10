import MetricsStrip from './MetricsStrip.jsx';
import ProductStrip from './ProductStrip.jsx';
import RouteCard from './RouteCard.jsx';

export default function ResultsDashboard({ result }) {
  return (
    <div id="results-section" className="results-section">
      <div className="divider" />
      <p className="section-title">3 — Results</p>

      <MetricsStrip metrics={result.metrics} />
      <ProductStrip porSku={result.metrics?.por_sku} />

      <p className="section-title">Routes</p>
      {(result.routes ?? []).map((routeObj, i) => (
        <RouteCard
          key={i}
          routeObj={routeObj}
          index={i}
          animationOffset={i * 350}
        />
      ))}
    </div>
  );
}
