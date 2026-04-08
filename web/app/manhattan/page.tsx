"use client";

import { useEffect, useState } from "react";
import { ManhattanPlot } from "@/components/manhattan-plot";
import { loadMetadata } from "@/lib/data";
import type { DisorderMeta } from "@/lib/data";

export default function ManhattanPage() {
  const [disorders, setDisorders] = useState<DisorderMeta[]>([]);

  useEffect(() => {
    loadMetadata().then((m) => setDisorders(m.disorders));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-2xl font-bold">Manhattan Overlay</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Multi-disorder Manhattan plot. Select up to 3 disorders to overlay.
          Each color represents a different disorder. Red dashed line = genome-wide significance (5×10⁻⁸).
        </p>
      </div>
      {disorders.length > 0 && <ManhattanPlot disorders={disorders} />}
    </div>
  );
}
