import { DisorderNetwork } from "@/components/disorder-network";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function NetworkPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-2xl font-bold">Disorder Network</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Force-directed network of psychiatric disorders. Node size = number of significant loci.
          Edge thickness = genetic correlation strength. Red edges = positive correlation.
          Hover a node to highlight its connections.
        </p>
      </div>
      <DisorderNetwork />
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base">How to read this</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-zinc-400">
          <p>
            Each <span className="text-zinc-200">node</span> is a psychiatric disorder. <span className="text-zinc-200">Node size</span> reflects how many genome-wide significant SNPs were found — larger nodes have more known genetic associations.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li><span className="text-zinc-200">Edges (lines)</span> connect disorders that share genetic risk variants. Thicker edges = stronger genetic correlation.</li>
            <li><span className="text-red-400">Red edges</span> = positive correlation (shared risk). <span className="text-blue-400">Blue edges</span> = negative correlation (opposite effects).</li>
            <li>Disorders that <span className="text-zinc-200">cluster together</span> form genetic "families" — they share underlying biology even if their symptoms differ.</li>
          </ul>
          <p className="text-xs text-zinc-500">
            Hover over a node to highlight its connections. Isolated nodes (like PTSD) had too few shared SNPs to compute reliable correlations — this often reflects smaller GWAS sample sizes rather than true genetic independence.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
