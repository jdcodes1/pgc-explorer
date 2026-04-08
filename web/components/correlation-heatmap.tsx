"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { CorrelationMatrix } from "@/lib/data";
import { loadCorrelationMatrix } from "@/lib/data";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export function CorrelationHeatmap() {
  const [data, setData] = useState<CorrelationMatrix | null>(null);

  useEffect(() => {
    loadCorrelationMatrix().then(setData);
  }, []);

  if (!data) {
    return <div className="flex h-96 items-center justify-center text-zinc-500">Loading correlation data...</div>;
  }

  return (
    <Plot
      data={[
        {
          z: data.values,
          x: data.labels,
          y: data.labels,
          type: "heatmap",
          colorscale: [
            [0, "#2563eb"],
            [0.5, "#18181b"],
            [1, "#dc2626"],
          ],
          zmin: -1,
          zmax: 1,
          hovertemplate: "%{x} ↔ %{y}<br>rg = %{z:.3f}<extra></extra>",
          showscale: true,
          colorbar: {
            title: { text: "Genetic Correlation (rg)", side: "right", font: { color: "#a1a1aa" } },
            tickfont: { color: "#a1a1aa" },
          },
        },
      ]}
      layout={{
        width: 700,
        height: 700,
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#a1a1aa", family: "monospace" },
        xaxis: { side: "bottom", tickangle: -45 },
        yaxis: { autorange: "reversed" },
        margin: { l: 100, r: 40, t: 20, b: 100 },
      }}
      config={{ responsive: true, displayModeBar: false }}
    />
  );
}
