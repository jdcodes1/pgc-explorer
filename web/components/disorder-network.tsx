"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { loadNetworkGraph } from "@/lib/data";
import type { NetworkGraph, NetworkNode } from "@/lib/data";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export function DisorderNetwork() {
  const [graph, setGraph] = useState<NetworkGraph | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 1100, h: 650 });

  useEffect(() => {
    loadNetworkGraph().then(setGraph);
  }, []);

  useEffect(() => {
    function handleResize() {
      if (containerRef.current) {
        const w = containerRef.current.offsetWidth;
        setDims({ w, h: Math.max(500, Math.min(700, w * 0.55)) });
      }
    }
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const { id, sigLoci, color } = node as NetworkNode & { x: number; y: number };
      const size = Math.sqrt(sigLoci || 50) * 0.6;
      const isHighlighted =
        hovered === null ||
        hovered === id ||
        graph?.links.some((l) => {
          const src = typeof l.source === "string" ? l.source : (l.source as any).id;
          const tgt = typeof l.target === "string" ? l.target : (l.target as any).id;
          return (src === hovered && tgt === id) || (tgt === hovered && src === id);
        });

      ctx.globalAlpha = isHighlighted ? 1 : 0.15;

      // Glow effect for hovered node
      if (hovered === id) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 6, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.15;
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Label
      const fontSize = Math.max(12 / globalScale, 3);
      ctx.font = `600 ${fontSize}px var(--font-geist-mono), monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#d4d4d8";
      ctx.fillText(id, node.x, node.y + size + 4);

      ctx.globalAlpha = 1;
    },
    [hovered, graph]
  );

  const linkCanvasObject = useCallback(
    (link: any, ctx: CanvasRenderingContext2D) => {
      const sourceId = typeof link.source === "string" ? link.source : link.source.id;
      const targetId = typeof link.target === "string" ? link.target : link.target.id;
      const isHighlighted = hovered === null || hovered === sourceId || hovered === targetId;

      ctx.globalAlpha = isHighlighted ? 0.5 : 0.04;
      ctx.beginPath();
      ctx.moveTo(link.source.x, link.source.y);
      ctx.lineTo(link.target.x, link.target.y);
      ctx.strokeStyle = link.weight > 0 ? "#ef4444" : "#3b82f6";
      ctx.lineWidth = Math.abs(link.weight) * 6;
      ctx.stroke();
      ctx.globalAlpha = 1;
    },
    [hovered]
  );

  if (!graph) {
    return (
      <div className="flex h-[500px] items-center justify-center rounded-xl border border-zinc-800/60 bg-zinc-900/30 text-zinc-600">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-500" />
          <p className="text-sm">Loading network data...</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/30"
    >
      <ForceGraph2D
        graphData={graph}
        width={dims.w}
        height={dims.h}
        backgroundColor="transparent"
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        onNodeHover={(node: any) => setHovered(node?.id || null)}
        cooldownTicks={100}
        linkDirectionalParticles={0}
      />
    </div>
  );
}
