// frontend/src/components/ForceGraphPanel.jsx
import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import AlephCard from './AlephCard';

export default function ForceGraphPanel({ accountId }) {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  
  // Interactive Hover Highlighting states
  const [hoverNode, setHoverNode] = useState(null);
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const [highlightLinks, setHighlightLinks] = useState(new Set());

  const containerRef = useRef(null);
  const fgRef = useRef(null);
  const [canvasWidth, setCanvasWidth] = useState(500);

  useEffect(() => {
    if (!accountId) return;

    setLoading(true);
    setError(false);
    setHoverNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());

    // Vite proxy strips /api prefix → FastAPI receives /graph/subgraph/{id}
    fetch(`/api/graph/subgraph/${accountId}`)
      .then(res => {
        if (!res.ok) throw new Error(`AuraDB query failed: ${res.status}`);
        return res.json();
      })
      .then(data => {
        setGraphData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('[ForceGraphPanel] Fetch failure:', err);
        setError(true);
        setLoading(false);
      });
  }, [accountId]);

  // Measure container width after mount
  useEffect(() => {
    if (containerRef.current) {
      setCanvasWidth(containerRef.current.clientWidth - 64);
    }
  }, []);

  // Update highlight tracking lists
  const handleNodeHover = node => {
    const nextHighlightNodes = new Set();
    const nextHighlightLinks = new Set();

    if (node) {
      nextHighlightNodes.add(node.id);
      // Find all adjacent nodes and connecting edges
      graphData.links.forEach(link => {
        // Link objects dynamically have .source.id and .target.id in react-force-graph-2d, or raw strings
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;

        if (sourceId === node.id) {
          nextHighlightNodes.add(targetId);
          nextHighlightLinks.add(link);
        } else if (targetId === node.id) {
          nextHighlightNodes.add(sourceId);
          nextHighlightLinks.add(link);
        }
      });
    }

    setHoverNode(node || null);
    setHighlightNodes(nextHighlightNodes);
    setHighlightLinks(nextHighlightLinks);
  };

  // Role-based color coding for multi-hop layering chain nodes [Technical Specification]
  const drawNodeCanvas = (node, ctx, globalScale) => {
    const isTarget = String(node.id) === String(accountId);
    const role = node.role || (isTarget ? 'target' : 'destination');

    // Highlight filter
    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);
    
    // Apply dimming effect to unrelated nodes when hovering
    ctx.globalAlpha = isHighlighted ? 1.0 : 0.15;

    // Radius by role — target is largest
    const radius = role === 'target' ? 8 : role === 'intermediary' ? 5 : 4;

    // Color palette: target=Terracotta, intermediary=Muted Orange, destination=Sage Green
    let coreColor, haloColor, strokeColor;
    if (role === 'target') {
      coreColor   = '#C07A50';
      haloColor   = 'rgba(192, 122, 80, 0.25)';
      strokeColor = '#9A5F38';
    } else if (role === 'intermediary') {
      coreColor   = '#D08A60';
      haloColor   = 'rgba(208, 138, 96, 0.20)';
      strokeColor = '#B06A40';
    } else {
      coreColor   = '#99B29B';
      haloColor   = 'rgba(153, 178, 155, 0.18)';
      strokeColor = '#7B9B7E';
    }

    // Outer halo
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius + 3, 0, 2 * Math.PI, false);
    ctx.fillStyle = haloColor;
    ctx.fill();

    // Core node fill
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    ctx.fillStyle = coreColor;
    ctx.fill();

    // Stroke ring
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 0.6 / globalScale;
    ctx.stroke();

    // Label — only render when zoomed in enough to avoid clutter
    if (globalScale > 0.6) {
      const fontSize = Math.max(8 / globalScale, 1);
      ctx.font = `${fontSize}px 'JetBrains Mono', monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#6B6864';
      ctx.fillText(String(node.id), node.x, node.y + radius + 2);
    }

    // Reset alpha
    ctx.globalAlpha = 1.0;
  };

  return (
    <AlephCard className="p-8 h-[480px]">
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-start mb-4 shrink-0">
          <div>
            <span className="text-[9px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">
              Topological Mapping · 2-Hop Layering Chain
            </span>
            <h3 className="text-xl font-serif font-bold text-[#2D2D2D] mt-0.5">
              Neighborhood Graph Overview
            </h3>
            <p className="text-xs text-[#6B6864] font-light mt-0.5">
              Live AuraDB subgraph for Account {accountId || '—'}
            </p>
          </div>
          <div className="text-right space-y-1">
            <span className="text-[10px] font-mono bg-[#FAF7F2] border border-[#EAE1D4] px-2 py-1 rounded text-[#6B6864] block">
              {graphData.nodes.length} Nodes · {graphData.links.length} Edges
            </span>
            {/* Role legend */}
            <div className="flex items-center space-x-2 justify-end">
              <span className="flex items-center space-x-1 text-[8px] font-mono text-[#6B6864]">
                <span className="w-2 h-2 rounded-full bg-[#C07A50] inline-block" />
                <span>Target</span>
              </span>
              <span className="flex items-center space-x-1 text-[8px] font-mono text-[#6B6864]">
                <span className="w-2 h-2 rounded-full bg-[#D08A60] inline-block" />
                <span>Pass-through</span>
              </span>
              <span className="flex items-center space-x-1 text-[8px] font-mono text-[#6B6864]">
                <span className="w-2 h-2 rounded-full bg-[#99B29B] inline-block" />
                <span>Destination</span>
              </span>
            </div>
          </div>
        </div>

        {/* Canvas area */}
        <div ref={containerRef} className="flex-1 rounded-lg overflow-hidden border border-[#EAE1D4] bg-[#FAF7F2]/40 relative">
          {loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center space-y-3">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-[#99B29B]" />
              <p className="text-[10px] text-[#6B6864] uppercase tracking-widest font-mono">
                Querying AuraDB Cloud Subgraph...
              </p>
            </div>
          )}
          {error && !loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center space-y-2">
              <span className="text-[10px] uppercase tracking-widest text-[#C07A50] font-bold">
                AuraDB Offline
              </span>
              <p className="text-xs text-[#6B6864] font-mono">
                Seed the database and ensure the backend is connected.
              </p>
            </div>
          )}
          {!loading && !error && graphData.nodes.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center space-y-2">
              <span className="text-[10px] uppercase tracking-widest text-[#6B6864] font-mono">
                No neighboring nodes found for {accountId}
              </span>
            </div>
          )}
          {!loading && !error && graphData.nodes.length > 0 && (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              width={canvasWidth}
              height={310}
              backgroundColor="transparent"
              nodeCanvasObject={drawNodeCanvas}
              nodeCanvasObjectMode={() => 'replace'}
              onNodeHover={handleNodeHover}
              linkColor={link => {
                if (highlightLinks.size === 0) return '#D6C8B5';
                return highlightLinks.has(link) ? '#C07A50' : 'rgba(214, 200, 181, 0.1)';
              }}
              linkWidth={link => (highlightLinks.has(link) ? 2.5 : 1.0)}
              linkDirectionalParticles={link => {
                if (highlightLinks.size === 0) return 3;
                return highlightLinks.has(link) ? 4 : 0;
              }}
              linkDirectionalParticleWidth={1.5}
              linkDirectionalParticleColor={() => '#C07A50'}
              linkDirectionalParticleSpeed={0.004}
              cooldownTicks={80}
              enableNodeDrag={true}
            />
          )}
        </div>
      </div>
    </AlephCard>
  );
}
