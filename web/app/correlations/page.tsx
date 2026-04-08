import { CorrelationHeatmap } from "@/components/correlation-heatmap";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function CorrelationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-2xl font-bold">Genetic Correlations</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Pairwise genetic correlation (rg) across psychiatric disorders.
          Red = positive correlation (shared genetic risk). Blue = negative.
          Based on effect size concordance of shared genome-wide significant SNPs.
        </p>
      </div>
      <CorrelationHeatmap />
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base">How to read this</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-zinc-400">
          <p>
            Each cell shows the <span className="text-zinc-200">genetic correlation (rg)</span> between two disorders — how much their genetic risk factors overlap. Values range from -1 to +1.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li><span className="text-red-400">Red (positive)</span> = SNPs that increase risk for one disorder also increase risk for the other. These disorders share genetic architecture.</li>
            <li><span className="text-blue-400">Blue (negative)</span> = SNPs that increase risk for one disorder tend to decrease risk for the other. Opposite genetic effects.</li>
            <li><span className="text-zinc-500">Near zero</span> = The disorders are genetically independent at these loci.</li>
          </ul>
          <p className="text-xs text-zinc-500">
            Note: These are beta correlations on shared genome-wide significant SNPs, not LD score regression estimates. Magnitudes may be inflated when few SNPs overlap — interpret directions (positive/negative) with more confidence than exact values.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
