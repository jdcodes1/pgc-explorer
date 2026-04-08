import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
}

export function StatCard({ label, value, sub }: StatCardProps) {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardContent className="pt-6">
        <p className="text-sm text-zinc-400">{label}</p>
        <p className="mt-1 font-mono text-3xl font-bold text-zinc-100">{value}</p>
        {sub && <p className="mt-1 text-xs text-zinc-500">{sub}</p>}
      </CardContent>
    </Card>
  );
}
