import { Building2, Shuffle, MapPin } from 'lucide-react';

const ZONE_META = {
  'granollers-center-01': ['Granollers Centre', 'Zone 01', Building2],
  'granollers-center-02': ['Granollers Centre', 'Zone 02', Building2],
  'granollers-center-03': ['Granollers Centre', 'Zone 03', Building2],
  'granollers-center-04': ['Granollers Centre', 'Zone 04', Building2],
  'granollers-center-05': ['Granollers Centre', 'Zone 05', Building2],
  'granollers-center-06': ['Granollers Centre', 'Zone 06', Building2],
  'granollers-center-07': ['Granollers Centre', 'Zone 07', Building2],
  'granollers-center-08': ['Granollers Centre', 'Zone 08', Building2],
  'zona-combinada-01':    ['Zona Combinada',    'Zone 01', Shuffle],
  'zona-combinada-02':    ['Zona Combinada',    'Zone 02', Shuffle],
};

export default function ZoneCard({ id, selected, onClick }) {
  const [name, num, Icon] = ZONE_META[id] ?? [id, '', MapPin];
  return (
    <button
      className={`zone-card${selected ? ' selected' : ''}`}
      onClick={onClick}
    >
      <span className="zone-icon"><Icon size={22} strokeWidth={1.5} /></span>
      <span className="zone-name">
        {name}<br /><strong>{num}</strong>
      </span>
      <span className="zone-id-lbl">{id}</span>
    </button>
  );
}
