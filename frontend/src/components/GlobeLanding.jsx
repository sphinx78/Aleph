import React, { useEffect, useRef, useCallback } from 'react';
import * as d3Geo from 'd3-geo';
import * as topojson from 'topojson-client';

export default function GlobeLanding({ onEnter }) {
  const canvasRef = useRef(null);
  // Use refs for animation state — avoids tearing down the canvas loop on every state change
  const scaleRef = useRef(240);
  const rotationRef = useRef([0, -20]);
  const isTransitioningRef = useRef(false);
  const animIdRef = useRef(null);
  const landRef = useRef(null);

  const handleZoomSequence = useCallback(() => {
    if (isTransitioningRef.current) return;
    isTransitioningRef.current = true;

    const interval = setInterval(() => {
      scaleRef.current += (900 - scaleRef.current) * 0.08;
      if (scaleRef.current >= 850) {
        clearInterval(interval);
        // Brief hold then transition
        setTimeout(onEnter, 120);
      }
    }, 16);
  }, [onEnter]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Transaction flow corridors (Nepal cross-border Hawala patterns)
    const corridors = [
      { from: [84.124, 28.394], to: [-0.127, 51.507] },  // Nepal → UK
      { from: [84.124, 28.394], to: [55.304, 25.263] },   // Nepal → UAE
      { from: [78.962, 20.593], to: [84.124, 28.394] },   // India → Nepal
    ];

    // Animated dash offset for flowing corridors
    let dashOffset = 0;

    const renderFrame = () => {
      const scale = scaleRef.current;
      const rotation = rotationRef.current;

      if (!isTransitioningRef.current) {
        rotation[0] += 0.18;
      }

      const projection = d3Geo.geoOrthographic()
        .scale(scale)
        .translate([width / 2, height / 2])
        .clipAngle(90)
        .rotate(rotation);

      const path = d3Geo.geoPath(projection, ctx);

      ctx.clearRect(0, 0, width, height);

      // 1. Globe fill (ocean)
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, scale, 0, 2 * Math.PI);
      ctx.fillStyle = '#FAF7F2';
      ctx.fill();

      // 2. Graticule gridlines
      const graticule = d3Geo.geoGraticule()();
      ctx.beginPath();
      path(graticule);
      ctx.strokeStyle = 'rgba(153, 178, 155, 0.18)';
      ctx.lineWidth = 0.5;
      ctx.stroke();

      // 3. Landmasses
      if (landRef.current) {
        ctx.beginPath();
        path(landRef.current);
        ctx.fillStyle = '#99B29B';
        ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,0.35)';
        ctx.lineWidth = 0.4;
        ctx.stroke();
      }

      // 4. Animated transaction flow arcs
      dashOffset = (dashOffset + 0.3) % 12;
      corridors.forEach(({ from, to }) => {
        const p1 = projection(from);
        const p2 = projection(to);
        if (!p1 || !p2) return;

        const d1 = d3Geo.geoDistance(from, projection.invert([width / 2, height / 2]));
        const d2 = d3Geo.geoDistance(to,   projection.invert([width / 2, height / 2]));

        if (d1 < Math.PI / 2 && d2 < Math.PI / 2) {
          const midX = (p1[0] + p2[0]) / 2;
          const midY = (p1[1] + p2[1]) / 2 - 45;

          // Shadow / glow trail
          ctx.beginPath();
          ctx.moveTo(p1[0], p1[1]);
          ctx.quadraticCurveTo(midX, midY, p2[0], p2[1]);
          ctx.strokeStyle = 'rgba(192, 122, 80, 0.12)';
          ctx.lineWidth = 4;
          ctx.setLineDash([]);
          ctx.stroke();

          // Active flow line
          ctx.beginPath();
          ctx.moveTo(p1[0], p1[1]);
          ctx.quadraticCurveTo(midX, midY, p2[0], p2[1]);
          ctx.strokeStyle = '#C07A50';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([5, 3]);
          ctx.lineDashOffset = -dashOffset;
          ctx.stroke();
          ctx.setLineDash([]);

          // Endpoint dots
          [p1, p2].forEach(p => {
            ctx.beginPath();
            ctx.arc(p[0], p[1], 3, 0, 2 * Math.PI);
            ctx.fillStyle = '#C07A50';
            ctx.fill();
          });
        }
      });

      // 5. Outer ring border
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, scale, 0, 2 * Math.PI);
      ctx.strokeStyle = '#EAE1D4';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // 6. Subtle outer pulse ring (Hawkes intensity visual)
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, scale + 8 + Math.sin(Date.now() / 800) * 3, 0, 2 * Math.PI);
      ctx.strokeStyle = 'rgba(153, 178, 155, 0.2)';
      ctx.lineWidth = 1;
      ctx.stroke();

      animIdRef.current = requestAnimationFrame(renderFrame);
    };

    // Load world geography data (low-res for fast load)
    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(data => {
        landRef.current = topojson.feature(data, data.objects.land);
        renderFrame();
      })
      .catch(() => {
        // Offline fallback — still animate without landmass
        renderFrame();
      });

    return () => {
      if (animIdRef.current) cancelAnimationFrame(animIdRef.current);
    };
  }, []); // Empty deps — loop runs entirely via refs, no restarts

  return (
    <div className="fixed inset-0 bg-[#FAF7F2] z-50 flex flex-col justify-center items-center font-sans">
      {/* Header copy */}
      <div className="text-center mb-8 max-w-xl px-6 animate-fade-up">
        <span className="text-xs uppercase tracking-[0.22em] text-[#C07A50] font-bold">
          Operational Security Engine
        </span>
        <h1 className="text-4xl font-serif text-[#2D2D2D] mt-3 mb-4 font-semibold tracking-tight leading-tight">
          AMLIOS-X System Platform
        </h1>
        <p className="text-sm text-[#6B6864] font-light leading-relaxed">
          Financial intelligence interface utilizing temporal graphs,<br />
          unsupervised community detection, and explainable ML to isolate<br />
          structured laundering operations across the transaction network.
        </p>
      </div>

      {/* Rotating globe canvas */}
      <div className="relative flex justify-center items-center">
        <canvas
          ref={canvasRef}
          width={500}
          height={500}
        />
      </div>

      {/* CTA button */}
      <button
        id="globe-enter-btn"
        onClick={handleZoomSequence}
        className="mt-8 px-8 py-3.5 border border-[#EAE1D4] text-[#2D2D2D] bg-white
          hover:bg-[#2D2D2D] hover:text-white hover:border-[#2D2D2D]
          rounded-full text-xs font-semibold tracking-widest uppercase
          transition-all duration-300 shadow-sm"
      >
        Initialize System Analytics
      </button>

      {/* Subtle footer descriptor */}
      <p className="mt-5 text-[10px] uppercase tracking-[0.2em] text-[#D6C8B5] font-semibold">
        Track 3 · Graph Intelligence · v3.1.2
      </p>
    </div>
  );
}
