import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/stat-card";

const vizCards = [
  {
    title: "Genetic Correlations",
    description: "12×12 heatmap of cross-disorder genetic correlations. Which disorders share the most genetic architecture?",
    href: "/correlations",
    badge: "Heatmap",
  },
  {
    title: "Manhattan Overlay",
    description: "Multi-disorder Manhattan plots. Overlay up to 3 disorders to spot shared genomic peaks.",
    href: "/manhattan",
    badge: "GWAS",
  },
  {
    title: "Disorder Network",
    description: "Force-directed network graph. Disorders cluster by genetic similarity, revealing hidden families.",
    href: "/network",
    badge: "Network",
  },
];

export default function Home() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="font-mono text-4xl font-bold tracking-tight">
          Psychiatric Genomics<br />
          <span className="text-zinc-400">Cross-Disorder Explorer</span>
        </h1>
        <p className="max-w-2xl text-lg text-zinc-400">
          Interactive visualization of genetic overlaps across psychiatric disorders.
          Built on{" "}
          <span className="text-zinc-200">1 billion+ rows</span> of GWAS summary
          statistics from the{" "}
          <span className="text-zinc-200">Psychiatric Genomics Consortium</span>.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Disorder Groups" value="12" sub="ADHD, SCZ, MDD, BIP..." />
        <StatCard label="Publications" value="52" sub="PGC GWAS studies" />
        <StatCard label="Total Variants" value="1B+" sub="Summary statistics" />
        <StatCard label="Data Source" value="HF" sub="OpenMed/pgc-*" />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {vizCards.map((card) => (
          <Link key={card.href} href={card.href}>
            <Card className="h-full bg-zinc-900 border-zinc-800 transition-colors hover:border-zinc-600">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{card.title}</CardTitle>
                  <Badge variant="secondary">{card.badge}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-zinc-400">{card.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
