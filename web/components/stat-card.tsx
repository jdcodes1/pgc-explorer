import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
}

export function StatCard({ label, value, sub }: StatCardProps) {
  return (
    <Card className="bg-zinc-900/60 border-zinc-800/60">
      <CardContent className="p-5">
        <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">{label}</p>
        <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-zinc-50">{value}</p>
        {sub && <p className="mt-1 text-sm text-zinc-500">{sub}</p>}
      </CardContent>
    </Card>
  );
}
