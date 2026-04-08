import { CorrelationHeatmap } from "@/components/correlation-heatmap";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function CorrelationsPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="font-mono text-xs font-medium uppercase tracking-widest text-emerald-400/70">
          Visualization
        </p>
        <h1 className="text-3xl font-bold tracking-tight">Genetic Correlations</h1>
        <p className="max-w-2xl text-base leading-relaxed text-zinc-400">
          Pairwise genetic correlation across psychiatric disorders.
          Red indicates positive correlation (shared genetic risk), blue indicates negative (opposite effects).
        </p>
      </div>

      <CorrelationHeatmap />

      <Card className="border-zinc-800/40 bg-zinc-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-zinc-400">How to read this</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-zinc-500">
          <p>
            Each cell shows the{" "}
            <span className="font-medium text-zinc-300">genetic correlation (rg)</span>{" "}
            between two disorders — how much their genetic risk factors overlap.
            Values range from -1 to +1.
          </p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              <span className="text-red-400">Red (positive)</span> = SNPs that
              increase risk for one disorder also increase risk for the other.
            </li>
            <li>
              <span className="text-blue-400">Blue (negative)</span> = SNPs that
              increase risk for one disorder tend to decrease risk for the other.
            </li>
            <li>
              <span className="text-zinc-600">Near zero</span> = The disorders are
              genetically independent at these loci.
            </li>
          </ul>
          <p className="text-xs text-zinc-600">
            Note: These are beta correlations on shared genome-wide significant SNPs,
            not LD score regression estimates. Magnitudes may be inflated when few SNPs
            overlap — interpret directions with more confidence than exact values.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
