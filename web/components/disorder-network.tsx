"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { loadNetworkGraph } from "@/lib/data";
import type { NetworkGraph, NetworkNode } from "@/lib/data";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export function DisorderNetwork() {
  const [graph, setGraph] = useState<NetworkGraph | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    loadNetworkGraph().then(setGraph);
  }, []);

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const { id, sigLoci, color } = node as NetworkNode & { x: number; y: number };
      const size = Math.sqrt(sigLoci || 50) * 0.5;
      const isHighlighted = hovered === null || hovered === id ||
        graph?.links.some(
          (l) => {
            const src = typeof l.source === "string" ? l.source : (l.source as any).id;
            const tgt = typeof l.target === "string" ? l.target : (l.target as any).id;
            return (src === hovered && tgt === id) || (tgt === hovered && src === id);
          }
        );

      ctx.globalAlpha = isHighlighted ? 1 : 0.2;

      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      ctx.font = `${12 / globalScale}px monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#e4e4e7";
      ctx.fillText(id, node.x, node.y + size + 2);

      ctx.globalAlpha = 1;
    },
    [hovered, graph]
  );

  const linkCanvasObject = useCallback(
    (link: any, ctx: CanvasRenderingContext2D) => {
      const sourceId = typeof link.source === "string" ? link.source : link.source.id;
      const targetId = typeof link.target === "string" ? link.target : link.target.id;
      const isHighlighted = hovered === null || hovered === sourceId || hovered === targetId;

      ctx.globalAlpha = isHighlighted ? 0.6 : 0.05;
      ctx.beginPath();
      ctx.moveTo(link.source.x, link.source.y);
      ctx.lineTo(link.target.x, link.target.y);
      ctx.strokeStyle = link.weight > 0 ? "#ef4444" : "#3b82f6";
      ctx.lineWidth = Math.abs(link.weight) * 5;
      ctx.stroke();
      ctx.globalAlpha = 1;
    },
    [hovered]
  );

  if (!graph) {
    return <div className="flex h-96 items-center justify-center text-zinc-500">Loading network data...</div>;
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 overflow-hidden">
      <ForceGraph2D
        graphData={graph}
        width={1100}
        height={600}
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
