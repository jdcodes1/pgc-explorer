import { DisorderNetwork } from "@/components/disorder-network";

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
    </div>
  );
}
