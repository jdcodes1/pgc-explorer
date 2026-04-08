"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { CorrelationMatrix } from "@/lib/data";
import { loadCorrelationMatrix } from "@/lib/data";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export function CorrelationHeatmap() {
  const [data, setData] = useState<CorrelationMatrix | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState(700);

  useEffect(() => {
    loadCorrelationMatrix().then(setData);
  }, []);

  useEffect(() => {
    function handleResize() {
      if (containerRef.current) {
        const w = containerRef.current.offsetWidth;
        setSize(Math.min(w, 800));
      }
    }
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  if (!data) {
    return (
      <div className="flex h-[500px] items-center justify-center text-zinc-600">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-500" />
          <p className="text-sm">Loading correlation data...</p>
        </div>
      </div>
    );
  }

  // Null out the diagonal so it renders as empty/grey
  const maskedValues = data.values.map((row, i) =>
    row.map((val, j) => (i === j ? null : val))
  );

  return (
    <div ref={containerRef} className="flex justify-center rounded-xl border border-zinc-800/60 bg-zinc-900/30 p-4">
      <Plot
        data={[
          {
            z: maskedValues,
            x: data.labels,
            y: data.labels,
            type: "heatmap",
            colorscale: [
              [0, "#1d4ed8"],
              [0.25, "#3b82f6"],
              [0.5, "#18181b"],
              [0.75, "#ef4444"],
              [1, "#b91c1c"],
            ],
            zmin: -1,
            zmax: 1,
            connectgaps: false,
            hoverongaps: false,
            hovertemplate:
              "<b>%{x}</b> ↔ <b>%{y}</b><br>rg = %{z:.3f}<extra></extra>",
            showscale: true,
            colorbar: {
              title: {
                text: "rg",
                side: "right",
                font: { color: "#a1a1aa", size: 13 },
              },
              tickfont: { color: "#71717a", size: 12 },
              thickness: 14,
              len: 0.6,
            },
          },
        ]}
        layout={{
          width: size,
          height: size,
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          font: { color: "#d4d4d8", family: "var(--font-geist-mono), monospace", size: 13 },
          xaxis: { side: "bottom", tickangle: -45, tickfont: { size: 12 } },
          yaxis: { autorange: "reversed", tickfont: { size: 12 } },
          margin: { l: 120, r: 60, t: 20, b: 120 },
        }}
        config={{ responsive: true, displayModeBar: false }}
      />
    </div>
  );
}
