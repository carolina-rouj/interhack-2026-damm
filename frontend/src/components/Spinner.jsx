import { useState, useEffect } from 'react';

const MSGS = [
  'Solving routes…',
  'Optimizing pallets…',
  'Assigning trucks…',
  'Calculating costs…',
  'Finalizing delivery plan…',
];

export default function Spinner() {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx(i => (i + 1) % MSGS.length), 950);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="spinner-wrap">
      <div className="spinner" />
      <p className="solving-text"><span>{MSGS[idx]}</span></p>
    </div>
  );
}
