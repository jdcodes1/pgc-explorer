"use client";

import { useEffect, useState } from "react";
import { ManhattanPlot } from "@/components/manhattan-plot";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { loadMetadata } from "@/lib/data";
import type { DisorderMeta } from "@/lib/data";

export default function ManhattanPage() {
  const [disorders, setDisorders] = useState<DisorderMeta[]>([]);

  useEffect(() => {
    loadMetadata().then((m) => setDisorders(m.disorders));
  }, []);

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="font-mono text-xs font-medium uppercase tracking-widest text-emerald-400/70">
          Visualization
        </p>
        <h1 className="text-3xl font-bold tracking-tight">Manhattan Overlay</h1>
        <p className="max-w-2xl text-base leading-relaxed text-zinc-400">
          Multi-disorder Manhattan plot. Select up to 3 disorders to overlay and
          spot shared genomic peaks across all 22 chromosomes.
        </p>
      </div>

      {disorders.length > 0 && <ManhattanPlot disorders={disorders} />}

      <Card className="border-zinc-800/40 bg-zinc-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-zinc-400">How to read this</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-zinc-500">
          <p>
            Each dot is a{" "}
            <span className="font-medium text-zinc-300">genetic variant (SNP)</span>{" "}
            tested for association with a disorder. The x-axis is genomic position
            (chromosomes 1-22), the y-axis is statistical significance.
          </p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              <span className="text-zinc-300">Higher dots = stronger evidence</span>{" "}
              of association. The y-axis shows -log10(p), so a dot at 8 means p = 10^-8.
            </li>
            <li>
              The <span className="text-red-400">red dashed line</span> is genome-wide
              significance (p = 5x10^-8). Dots above this line are robust associations.
            </li>
            <li>
              When overlaying disorders,{" "}
              <span className="text-zinc-300">peaks that align vertically</span> across
              colors indicate shared genetic risk loci.
            </li>
          </ul>
          <p className="text-xs text-zinc-600">
            Tip: Try overlaying Schizophrenia + Bipolar + Depression to see shared
            peaks, especially on chromosome 6 (the MHC region).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
