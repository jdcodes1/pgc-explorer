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
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-2xl font-bold">Manhattan Overlay</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Multi-disorder Manhattan plot. Select up to 3 disorders to overlay.
          Each color represents a different disorder. Red dashed line = genome-wide significance (5×10⁻⁸).
        </p>
      </div>
      {disorders.length > 0 && <ManhattanPlot disorders={disorders} />}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base">How to read this</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-zinc-400">
          <p>
            Each dot is a <span className="text-zinc-200">genetic variant (SNP)</span> tested for association with a disorder. The x-axis is genomic position (chromosomes 1–22), the y-axis is statistical significance.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li><span className="text-zinc-200">Higher dots = stronger evidence</span> of association. The y-axis shows -log₁₀(p), so a dot at 8 means p = 10⁻⁸.</li>
            <li>The <span className="text-red-400">red dashed line</span> is genome-wide significance (p = 5×10⁻⁸). Dots above this line are considered robust associations.</li>
            <li>When overlaying multiple disorders, <span className="text-zinc-200">peaks that align vertically</span> across colors indicate shared genetic risk loci — the same genomic region affects both disorders.</li>
          </ul>
          <p className="text-xs text-zinc-500">
            Tip: Try overlaying Schizophrenia + Bipolar + Depression to see shared peaks, especially on chromosome 6 (the MHC region — the strongest psychiatric GWAS signal).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
