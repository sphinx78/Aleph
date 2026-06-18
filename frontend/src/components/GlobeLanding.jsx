import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3-geo';
import * as topojson from 'topojson-client';

export default function GlobeLanding({ onEnter }) {
  const canvasRef = useRef(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [globeScale, setGlobeScale] = useState(240);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Set up projection & path generator
    const projection = d3.geoOrthographic()
      .scale(globeScale)
      .translate([width / 2, height / 2])
      .clipAngle(90);

    const path = d3.geoPath(projection, ctx);

    let rotation = [0, -20];
    let animId;
    let land = null;

    // Simulated cross-border Hundi / Hawala flow coordinates
    const transactionCorridors = [
      { from: [84.124, 28.394], to: [-0.127, 51.507] }, // Nepal -> UK
      { from: [84.124, 28.394], to: [55.304, 25.263] },  // Nepal -> UAE
      { from: [78.962, 20.593], to: [84.124, 28.394] }   // India -> Nepal
    ];

    const renderLoop = () => {
      ctx.clearRect(0, 0, width, height);

      // Continuous gentle rotation when not transitioning
      if (!isTransitioning) {
        rotation[0] += 0.2;
        projection.rotate(rotation);
      }

      // 1. Globe Backdrop (Oceans)
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, projection.scale(), 0, 2 * Math.PI);
      ctx.fillStyle = '#FAF7F2';
      ctx.fill();

      // 2. Graticules (Gridlines)
      ctx.beginPath();
      const graticule = d3.geoGraticule()();
      path(graticule);
      ctx.strokeStyle = 'rgba(153, 178, 155, 0.2)';
      ctx.lineWidth = 0.5;
      ctx.stroke();

      // 3. Landmasses (Draw if loaded, else render abstract wireframe)
      if (land) {
        ctx.beginPath();
        path(land);
        ctx.fillStyle = '#99B29B'; // Main Sage Green
        ctx.fill();
      } else {
        // Abstract aesthetic placeholder/wireframe for offline mode
        ctx.beginPath();
        ctx.arc(width / 2, height / 2, projection.scale() - 10, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(153, 178, 155, 0.4)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // 4. Cross-Border Transaction Arcs
      transactionCorridors.forEach(corridor => {
        const p1 = projection(corridor.from);
        const p2 = projection(corridor.to);

        // Check if endpoints are visible on the globe's face
        const d1 = d3.geoDistance(corridor.from, projection.invert([width/2, height/2]));
        const d2 = d3.geoDistance(corridor.to, projection.invert([width/2, height/2]));

        if (d1 < Math.PI / 2 && d2 < Math.PI / 2) {
          ctx.beginPath();
          ctx.moveTo(p1[0], p1[1]);
          
          // Calculate midpoint with height offset for a 3D arc effect
          const midX = (p1[0] + p2[0]) / 2;
          const midY = (p1[1] + p2[1]) / 2 - 40; 
          ctx.quadraticCurveTo(midX, midY, p2[0], p2[1]);
          
          ctx.strokeStyle = '#C07A50'; // Terracotta accent
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 2]); // Dotted flow line
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });

      // 5. Outer Ring
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, projection.scale(), 0, 2 * Math.PI);
      ctx.strokeStyle = '#EAE1D4';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      animId = requestAnimationFrame(renderLoop);
    };

    // Fetch low-res geographic data to keep initial load fast
    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then(res => {
        if (!res.ok) throw new Error("Failed to load map data");
        return res.json();
      })
      .then(worldData => {
        land = topojson.feature(worldData, worldData.objects.land);
        renderLoop();
      })
      .catch(err => {
        console.warn("Could not retrieve online geographic data, using abstract fallback:", err);
        // Still run the loop to keep the animation going with offline fallback UI
        renderLoop();
      });

    return () => cancelAnimationFrame(animId);
  }, [globeScale, isTransitioning]);

  const handleZoomSequence = () => {
    setIsTransitioning(true);
    let currentScale = 240;
    
    // Smooth ease-in zoom effect
    const interval = setInterval(() => {
      currentScale += (900 - currentScale) * 0.08;
      setGlobeScale(currentScale);
      
      if (currentScale >= 850) {
        clearInterval(interval);
        onEnter();
      }
    }, 16);
  };

  return (
    <div className="fixed inset-0 bg-[#FAF7F2] z-50 flex flex-col justify-center items-center font-sans">
      <div className="text-center mb-6 max-w-xl px-6">
        <span className="text-xs uppercase tracking-[0.2em] text-[#C07A50] font-bold">
          Operational Security Engine
        </span>
        <h1 className="text-4xl font-serif text-[#2D2D2D] mt-2 mb-4 font-semibold tracking-tight">
          AMLIOS-X System Platform
        </h1>
        <p className="text-sm text-[#6B6864] font-light leading-relaxed">
          Financial intelligence interface. Utilizing temporal graphs, unsupervised community detection, 
          and explainable ML to identify and isolate structured laundering operations.
        </p>
      </div>

      <div className="relative flex justify-center items-center">
        <canvas 
          ref={canvasRef} 
          width={500} 
          height={500} 
          className="transition-transform duration-700 ease-out hover:scale-102"
        />
      </div>

      <button
        onClick={handleZoomSequence}
        className="mt-8 px-8 py-3.5 border border-[#EAE1D4] text-[#2D2D2D] bg-white hover:bg-[#2D2D2D] hover:text-white hover:border-[#2D2D2D] rounded-full text-xs font-semibold tracking-widest uppercase transition-all duration-300 shadow-sm"
      >
        Initialize System Analytics
      </button>
    </div>
  );
}
