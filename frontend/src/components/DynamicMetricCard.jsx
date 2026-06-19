import { Activity, ChevronRight, Network, Triangle } from 'lucide-react';
import { useRef, useState } from 'react';

const variantMeta = {
  mint: {
    className: 'neon-metric-card--mint',
    Icon: Network,
  },
  violet: {
    className: 'neon-metric-card--violet',
    Icon: Activity,
  },
  solar: {
    className: 'neon-metric-card--solar',
    Icon: Triangle,
  },
};

export default function DynamicMetricCard({ children, title, uppercaseSub, value, trend, variant = 'mint' }) {
  const cardRef = useRef(null);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const meta = variantMeta[variant] ?? variantMeta.mint;
  const Icon = meta.Icon;

  const handleMouseMove = (e) => {
    const card = cardRef.current;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setCoords({ x, y });
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className={`neon-metric-card ${meta.className}`}
      style={{
        '--spot-x': `${coords.x}px`,
        '--spot-y': `${coords.y}px`,
      }}
    >
      <div className="neon-metric-card__glass" />
      <div className="neon-metric-card__icon" aria-hidden="true">
        <Icon size={20} strokeWidth={2.25} />
      </div>

      <div className="neon-metric-card__content">
        <div className="neon-metric-card__topline">
          <span>{uppercaseSub}</span>
          {trend && <strong>{trend.value}</strong>}
        </div>
        <h3>{title}</h3>

        {value && <p className="neon-metric-card__value">{value}</p>}
        <p className="neon-metric-card__copy">{children}</p>
      </div>

      <div className="neon-metric-card__footer">
        <div className="neon-metric-card__dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <button type="button" aria-label={`Open ${title} details`}>
          <span>Open</span>
          <ChevronRight size={15} strokeWidth={2.4} />
        </button>
      </div>
    </div>
  );
}
