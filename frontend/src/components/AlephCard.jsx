import React, { useRef, useState } from 'react';

export default function AlephCard({ children, className = "" }) {
  const cardRef = useRef(null);
  const [coords, setCoords] = useState({ x: 0, y: 0 });

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
      className={`relative overflow-hidden bg-white/75 backdrop-blur-md rounded-xl border border-[#EAE1D4] 
        transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 group ${className}`}
    >
      {/* Interactive cursor tracking gradient background */}
      <div 
        className="absolute inset-0 pointer-events-none transition-opacity duration-300 opacity-0 group-hover:opacity-100"
        style={{
          background: `radial-gradient(240px circle at ${coords.x}px ${coords.y}px, rgba(153, 178, 155, 0.15), transparent 80%)`
        }}
      />
      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </div>
  );
}
