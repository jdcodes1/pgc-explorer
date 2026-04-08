import { DisorderNetwork } from "@/components/disorder-network";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function NetworkPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="font-mono text-xs font-medium uppercase tracking-widest text-emerald-400/70">
          Visualization
        </p>
        <h1 className="text-3xl font-bold tracking-tight">Disorder Network</h1>
        <p className="max-w-2xl text-base leading-relaxed text-zinc-400">
          Force-directed network of psychiatric disorders. Node size reflects the number
          of significant loci. Edge thickness indicates genetic correlation strength.
          Hover to highlight connections.
        </p>
      </div>

      <DisorderNetwork />

      <Card className="border-zinc-800/40 bg-zinc-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-zinc-400">How to read this</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-zinc-500">
          <p>
            Each <span className="font-medium text-zinc-300">node</span> is a
            psychiatric disorder.{" "}
            <span className="font-medium text-zinc-300">Node size</span> reflects how
            many genome-wide significant SNPs were found — larger nodes have more known
            genetic associations.
          </p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              <span className="text-zinc-300">Edges</span> connect disorders that share
              genetic risk variants. Thicker edges = stronger genetic correlation.
            </li>
            <li>
              <span className="text-red-400">Red edges</span> = positive correlation
              (shared risk). <span className="text-blue-400">Blue edges</span> = negative
              (opposite effects).
            </li>
            <li>
              Disorders that{" "}
              <span className="text-zinc-300">cluster together</span> form genetic
              &quot;families&quot; — they share underlying biology even if symptoms differ.
            </li>
          </ul>
          <p className="text-xs text-zinc-600">
            Hover over a node to highlight its connections. Isolated nodes (like PTSD)
            had too few shared SNPs to compute reliable correlations — this often reflects
            smaller sample sizes rather than true genetic independence.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
