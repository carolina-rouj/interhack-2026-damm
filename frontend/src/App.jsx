import { useState, useEffect } from 'react';
import { listZones, solve } from './api.js';
import Header from './components/Header.jsx';
import ZoneGrid from './components/ZoneGrid.jsx';
import Controls from './components/Controls.jsx';
import Spinner from './components/Spinner.jsx';
import ResultsDashboard from './components/ResultsDashboard.jsx';

export default function App() {
  const [zones, setZones]     = useState([]);
  const [selected, setSelected] = useState(null);
  const cajas = 60;
  const [status, setStatus]   = useState('idle'); // idle | loading | done | error
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState('');

  useEffect(() => {
    listZones()
      .then(data => setZones(data.zonas ?? []))
      .catch(() => setError('Could not load zones. Is the server running?'));
  }, []);

  async function runSimulation() {
    if (!selected) return;
    setStatus('loading');
    setResult(null);
    setError('');
    try {
      const data = await solve(selected, cajas);
      setResult(data);
      setStatus('done');
      setTimeout(() => {
        document.getElementById('results-section')
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 60);
    } catch (err) {
      setError(`Simulation failed: ${err.message}`);
      setStatus('error');
    }
  }

  return (
    <>
      <Header />
      <div className="main">
        <p className="section-title">1 — Select a Delivery Zone</p>
        <ZoneGrid zones={zones} selected={selected} onSelect={setSelected} />

        <p className="section-title">2 — Configure &amp; Run</p>
        <Controls
          disabled={!selected || status === 'loading'}
          onSimulate={runSimulation}
        />

        {status === 'loading' && <Spinner />}

        {(status === 'error') && (
          <div className="error-banner">{error}</div>
        )}

        {status === 'done' && result && (
          <ResultsDashboard result={result} />
        )}
      </div>
    </>
  );
}
