import React, { useRef, useState } from 'react';

export default function DynamicMetricCard({ children, title, uppercaseSub, value, trend }) {
  const cardRef = useRef(null);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

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
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative overflow-hidden bg-white rounded-xl border border-[#EAE1D4] p-6 transition-all duration-300 hover:shadow-md group"
    >
      {/* Interactive cursor tracking gradient background */}
      <div 
        className="absolute inset-0 pointer-events-none transition-opacity duration-300 opacity-0 group-hover:opacity-100"
        style={{
          background: `radial-gradient(180px circle at ${coords.x}px ${coords.y}px, rgba(153, 178, 155, 0.08), transparent 80%)`
        }}
      />

      <div className="relative z-10 flex flex-col justify-between h-full">
        <div>
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">
              {uppercaseSub}
            </span>
            {trend && (
              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                trend.direction === 'up' ? 'bg-[#99B29B]/15 text-[#99B29B]' : 'bg-red-50 text-red-600'
              }`}>
                {trend.value}
              </span>
            )}
          </div>
          <h3 className="text-xl font-serif text-[#2D2D2D] font-medium tracking-tight mb-4">
            {title}
          </h3>
        </div>

        <div>
          {value && (
            <p className="text-3xl font-mono tracking-tight text-[#2D2D2D] font-semibold mb-2">
              {value}
            </p>
          )}
          <div className="text-xs text-[#6B6864] leading-relaxed font-light">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
