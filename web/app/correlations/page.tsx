import { CorrelationHeatmap } from "@/components/correlation-heatmap";

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
    </div>
  );
}
