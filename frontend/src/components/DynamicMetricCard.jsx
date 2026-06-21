import { Activity, ChevronRight, Network, Triangle } from 'lucide-react';

const variantMeta = {
  mint: {
    parentClass: 'ux-parent--mint',
    Icon: Network,
  },
  violet: {
    parentClass: 'ux-parent--violet',
    Icon: Activity,
  },
  solar: {
    parentClass: 'ux-parent--solar',
    Icon: Triangle,
  },
};

export default function DynamicMetricCard({ children, title, uppercaseSub, value, trend, variant = 'mint' }) {
  const meta = variantMeta[variant] ?? variantMeta.mint;
  const Icon = meta.Icon;

  return (
    <div className={`ux-parent ${meta.parentClass}`}>
      <div className="ux-card">
        {/* Concentric orbit circles — stacked in Z-space */}
        <div className="ux-logo" aria-hidden="true">
          <span className="ux-circle"></span>
          <span className="ux-circle"></span>
          <span className="ux-circle"></span>
          <span className="ux-circle"></span>
          <span className="ux-circle" style={{ display: 'grid', placeContent: 'center' }}>
            <Icon size={20} strokeWidth={2.25} color="#fff" />
          </span>
        </div>

        {/* Glass layer — pops forward in 3D */}
        <div className="ux-glass"></div>

        {/* Content layer — elevated in Z-space */}
        <div className="ux-content">
          {uppercaseSub && (
            <span style={{
              display: 'block',
              fontSize: '0.65rem',
              fontWeight: 800,
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              color: 'var(--ux-title)',
              opacity: 0.7,
              marginBottom: '0.35rem',
              fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif"
            }}>
              {uppercaseSub}
              {trend && <strong style={{ marginLeft: '0.65rem', letterSpacing: '0.05em' }}>{trend.value}</strong>}
            </span>
          )}
          <span className="ux-title">{title}</span>
          {value && (
            <span style={{
              display: 'block',
              marginTop: '0.55rem',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 'clamp(1.15rem, 2.5vw, 1.45rem)',
              fontWeight: 800,
              color: 'var(--ux-title)',
              letterSpacing: '-0.02em',
            }}>
              {value}
            </span>
          )}
          <span className="ux-text" style={{
            marginTop: '0.65rem',
            fontSize: '0.82rem',
            display: '-webkit-box',
            WebkitBoxOrient: 'vertical',
            WebkitLineClamp: 4,
            overflow: 'hidden',
          }}>
            {children}
          </span>
        </div>

        {/* Bottom action bar — 3D floating */}
        <div className="ux-bottom">
          <div className="ux-social">
            <button type="button" className="ux-social-btn" aria-label="Action 1">
              <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5" /></svg>
            </button>
            <button type="button" className="ux-social-btn" aria-label="Action 2">
              <svg viewBox="0 0 24 24"><rect x="7" y="7" width="10" height="10" rx="2" /></svg>
            </button>
            <button type="button" className="ux-social-btn" aria-label="Action 3">
              <svg viewBox="0 0 24 24"><path d="M12 5l7 12H5z" /></svg>
            </button>
          </div>
          <div className="ux-more">
            <button type="button" className="ux-more-btn" aria-label={`Open ${title} details`}>
              <span>Open</span>
            </button>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
