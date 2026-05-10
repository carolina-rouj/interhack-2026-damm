export default function ProductStrip({ porSku = {} }) {
  const entries = Object.entries(porSku);
  if (!entries.length) return null;

  return (
    <div className="products-strip">
      {entries.map(([sku, info]) => (
        <div key={sku} className="product-pill">
          <span className="pill-sku">{sku}</span>
          <span className="pill-name">{info.nombre ?? sku}</span>
          <span className="pill-count">{info.total_cajas ?? info.cajas} boxes</span>
        </div>
      ))}
    </div>
  );
}
