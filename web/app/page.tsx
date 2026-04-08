import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/stat-card";
import { Separator } from "@/components/ui/separator";

const vizCards = [
  {
    title: "Genetic Correlations",
    description:
      "9x9 heatmap of cross-disorder genetic correlations. Which disorders share the most genetic architecture?",
    href: "/correlations",
    badge: "Heatmap",
    color: "#dc2626",
  },
  {
    title: "Manhattan Overlay",
    description:
      "Multi-disorder Manhattan plots. Overlay up to 3 disorders to spot shared genomic peaks across chromosomes.",
    href: "/manhattan",
    badge: "GWAS",
    color: "#3b82f6",
  },
  {
    title: "Disorder Network",
    description:
      "Force-directed network graph. Disorders cluster by genetic similarity, revealing hidden families.",
    href: "/network",
    badge: "Network",
    color: "#10b981",
  },
];

const disorders = [
  { name: "ADHD", snps: "7,033", color: "#e74c3c" },
  { name: "Anxiety", snps: "12,815", color: "#e67e22" },
  { name: "Autism", snps: "4,027", color: "#f1c40f" },
  { name: "Bipolar", snps: "5,346", color: "#2ecc71" },
  { name: "Depression", snps: "7,014", color: "#3498db" },
  { name: "Schizophrenia", snps: "112,770", color: "#1abc9c" },
  { name: "PTSD", snps: "618", color: "#e91e63" },
  { name: "Eating Disorders", snps: "348", color: "#ff9800" },
  { name: "Cross-Disorder", snps: "10,234", color: "#607d8b" },
];

export default function Home() {
  return (
    <div className="space-y-16">
      {/* Hero */}
      <div className="space-y-6 pt-4">
        <div className="space-y-3">
          <p className="font-mono text-sm font-medium uppercase tracking-widest text-emerald-400/80">
            Psychiatric Genomics Consortium
          </p>
          <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
            Cross-Disorder
            <br />
            <span className="text-zinc-500">Explorer</span>
          </h1>
        </div>
        <p className="max-w-2xl text-lg leading-relaxed text-zinc-400">
          Interactive visualization of genetic overlaps across psychiatric disorders.
          Built on{" "}
          <span className="font-medium text-zinc-200">1 billion+ rows</span> of GWAS
          summary statistics from the{" "}
          <span className="font-medium text-zinc-200">Psychiatric Genomics Consortium</span>,
          served via{" "}
          <span className="font-medium text-zinc-200">HuggingFace</span>.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        <StatCard label="Disorders Loaded" value="9" sub="of 12 disorder groups" />
        <StatCard label="Publications" value="52" sub="PGC GWAS studies" />
        <StatCard label="Significant SNPs" value="160K" sub="at p < 1e-5" />
        <StatCard label="Data Source" value="HF" sub="OpenMed/pgc-*" />
      </div>

      {/* Viz cards */}
      <div>
        <h2 className="mb-5 text-lg font-semibold text-zinc-300">Visualizations</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {vizCards.map((card) => (
            <Link key={card.href} href={card.href} className="group">
              <Card className="h-full border-zinc-800/60 bg-zinc-900/40 transition-all duration-300 group-hover:border-zinc-700 group-hover:bg-zinc-900/70">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-semibold">{card.title}</CardTitle>
                    <Badge
                      variant="outline"
                      className="border-zinc-700 text-xs"
                      style={{ color: card.color }}
                    >
                      {card.badge}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed text-zinc-500">{card.description}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      <Separator className="bg-zinc-800/50" />

      {/* Loaded disorders table */}
      <div>
        <h2 className="mb-2 text-lg font-semibold text-zinc-300">Loaded Disorders</h2>
        <p className="mb-5 text-sm text-zinc-500">
          Significant SNPs (p &lt; 10⁻⁵) extracted per disorder from the latest available PGC publication.
        </p>
        <div className="overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/40">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-zinc-800/60 text-xs font-medium uppercase tracking-wider text-zinc-500">
                <th className="px-5 py-3">Disorder</th>
                <th className="px-5 py-3 text-right">Significant SNPs</th>
                <th className="hidden px-5 py-3 text-right sm:table-cell">Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/40">
              {disorders.map((d) => {
                const count = parseInt(d.snps.replace(/,/g, ""), 10);
                const maxCount = 112770;
                const pct = ((count / maxCount) * 100).toFixed(1);
                return (
                  <tr key={d.name} className="transition-colors hover:bg-zinc-800/20">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: d.color }}
                        />
                        <span className="text-sm font-medium text-zinc-200">{d.name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-sm text-zinc-300">
                      {d.snps}
                    </td>
                    <td className="hidden px-5 py-3 text-right sm:table-cell">
                      <div className="flex items-center justify-end gap-3">
                        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-zinc-800">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.max(2, parseFloat(pct))}%`,
                              backgroundColor: d.color,
                              opacity: 0.7,
                            }}
                          />
                        </div>
                        <span className="w-12 text-right font-mono text-xs text-zinc-500">
                          {pct}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <Separator className="bg-zinc-800/50" />

      {/* Data pipeline explanation */}
      <div className="grid gap-8 sm:grid-cols-2">
        <div>
          <h2 className="mb-4 text-lg font-semibold text-zinc-300">How the data was extracted</h2>
          <div className="space-y-4 text-sm leading-relaxed text-zinc-500">
            <p>
              The Psychiatric Genomics Consortium publishes GWAS summary statistics
              across dozens of studies. These were historically scattered across
              Figshare, requiring manual downloads and format wrangling.
            </p>
            <p>
              The{" "}
              <span className="text-zinc-300">OpenMed project</span> converted all 52
              publications into clean Apache Parquet on HuggingFace, making them
              queryable with one line of Python.
            </p>
            <p>
              We use{" "}
              <span className="font-mono text-emerald-400/80">DuckDB</span> to query
              HuggingFace parquet files directly with predicate pushdown — only
              rows matching{" "}
              <span className="font-mono text-zinc-300">p &lt; 10⁻⁵</span> are
              downloaded, avoiding 50GB+ full dataset transfers.
            </p>
          </div>
        </div>
        <div>
          <h2 className="mb-4 text-lg font-semibold text-zinc-300">Pipeline &amp; snapshots</h2>
          <div className="space-y-4 text-sm leading-relaxed text-zinc-500">
            <div className="overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/40">
              <div className="space-y-0 divide-y divide-zinc-800/40">
                {[
                  ["1. Query", "DuckDB queries HuggingFace parquet with p-value filter"],
                  ["2. Normalize", "Column names unified across 52 publications"],
                  ["3. Correlate", "Beta correlation on shared SNPs per disorder pair"],
                  ["4. Export", "JSON snapshots: correlation matrix, Manhattan data, network graph"],
                  ["5. Deploy", "Static JSON served by Next.js on Vercel"],
                ].map(([step, desc]) => (
                  <div key={step} className="flex gap-4 px-5 py-3">
                    <span className="shrink-0 font-mono text-xs font-semibold text-emerald-400/70">
                      {step}
                    </span>
                    <span className="text-sm text-zinc-400">{desc}</span>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-xs text-zinc-600">
              Correlation values are beta correlations on shared genome-wide significant
              SNPs — a proxy for genetic correlation, not LD score regression. Directions
              are reliable; magnitudes may be inflated with few shared SNPs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
