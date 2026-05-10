import { Play } from 'lucide-react';

export default function Controls({ disabled, onSimulate }) {
  return (
    <div className="controls-row">
      <button
        className="simulate-btn"
        disabled={disabled}
        onClick={onSimulate}
      >
        <Play size={16} strokeWidth={2} style={{ verticalAlign: 'middle', marginRight: 8 }} />
        Run Simulation
      </button>
    </div>
  );
}
