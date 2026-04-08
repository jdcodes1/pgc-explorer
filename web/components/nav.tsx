"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Overview" },
  { href: "/correlations", label: "Correlations" },
  { href: "/manhattan", label: "Manhattan" },
  { href: "/network", label: "Network" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-zinc-800 bg-zinc-950">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-6">
        <Link href="/" className="font-mono text-sm font-bold tracking-tight text-zinc-100">
          PGC Explorer
        </Link>
        <div className="flex gap-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm transition-colors",
                pathname === link.href
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-100"
              )}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
