import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import AlephCard from './AlephCard';

export default function LayeringAlluvial({ pathData }) {
  const svgRef = useRef();

  useEffect(() => {
    if (!pathData || pathData.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 180;
    
    // Distribute transfer nodes horizontally across the canvas
    const stepX = width / (pathData.length);
    const nodeY = height / 2;

    const g = svg.append('g').attr('transform', 'translate(40, 0)');

    // 1. Draw connecting bezier flows between transaction nodes
    for (let i = 0; i < pathData.length - 1; i++) {
      const x1 = i * stepX + 30;
      const y1 = nodeY;
      const x2 = (i + 1) * stepX - 30;
      const y2 = nodeY;

      // Draw elegant bezier flow lines
      g.append('path')
        .attr('d', `M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`)
        .attr('fill', 'none')
        .attr('stroke', '#EAE1D4')
        .attr('stroke-width', 4)
        .attr('opacity', 0.8);

      // Draw inner active flow line
      const activePath = g.append('path')
        .attr('d', `M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`)
        .attr('fill', 'none')
        .attr('stroke', '#99B29B')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '8, 4');

      // Simple animated flow effect
      activePath.append('animate')
        .attr('attributeName', 'stroke-dashoffset')
        .attr('values', '12;0')
        .attr('dur', '1.5s')
        .attr('repeatCount', 'indefinite');
    }

    // 2. Draw account node points and labels
    pathData.forEach((node, i) => {
      const cx = i * stepX;

      // Outer boundary glow
      g.append('circle')
        .attr('cx', cx)
        .attr('cy', nodeY)
        .attr('r', 16)
        .attr('fill', '#FFFFFF')
        .attr('stroke', '#99B29B')
        .attr('stroke-width', 1.5)
        .attr('class', 'shadow-sm');

      // Inner indicator
      g.append('circle')
        .attr('cx', cx)
        .attr('cy', nodeY)
        .attr('r', 5)
        .attr('fill', '#C07A50');

      // Account ID label
      g.append('text')
        .attr('x', cx)
        .attr('y', nodeY - 24)
        .attr('text-anchor', 'middle')
        .attr('fill', '#2D2D2D')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .attr('font-family', 'monospace')
        .text(node.account_id);

      // Amount label (NPR)
      g.append('text')
        .attr('x', cx)
        .attr('y', nodeY + 30)
        .attr('text-anchor', 'middle')
        .attr('fill', '#6B6864')
        .attr('font-size', '10px')
        .text(`NPR ${(node.amount || 0).toLocaleString()}`);
    });

  }, [pathData]);

  return (
    <AlephCard className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <span className="text-[9px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">
            Layering Analysis
          </span>
          <h4 className="text-sm font-serif font-semibold text-[#2D2D2D]">
            Multi-Hop Transaction Path View
          </h4>
        </div>
        <span className="text-xs text-[#99B29B] bg-[#99B29B]/10 px-3 py-1 rounded-full font-bold">
          Amount Conservation ≥ 98%
        </span>
      </div>
      <div className="overflow-x-auto">
        <svg ref={svgRef} width="880" height="180" />
      </div>
    </AlephCard>
  );
}
