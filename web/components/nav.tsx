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
    <nav className="sticky top-0 z-50 border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between px-4 sm:px-8 lg:px-12">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="4" cy="4" r="2.5" fill="currentColor" opacity="0.8" />
              <circle cx="12" cy="4" r="2.5" fill="currentColor" opacity="0.5" />
              <circle cx="8" cy="12" r="2.5" fill="currentColor" opacity="0.65" />
              <line x1="4" y1="4" x2="12" y2="4" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
              <line x1="4" y1="4" x2="8" y2="12" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
              <line x1="12" y1="4" x2="8" y2="12" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
            </svg>
          </div>
          <span className="font-mono text-sm font-semibold tracking-tight text-zinc-100">
            PGC Explorer
          </span>
        </Link>
        <div className="flex items-center gap-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200",
                pathname === link.href
                  ? "bg-zinc-800/80 text-zinc-50"
                  : "text-zinc-500 hover:bg-zinc-800/40 hover:text-zinc-200"
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
