"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { loadManhattanData } from "@/lib/data";
import type { ManhattanData, DisorderMeta } from "@/lib/data";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const CHR_LENGTHS: Record<number, number> = {
  1: 249e6, 2: 243e6, 3: 198e6, 4: 191e6, 5: 182e6, 6: 171e6,
  7: 159e6, 8: 146e6, 9: 141e6, 10: 136e6, 11: 135e6, 12: 134e6,
  13: 115e6, 14: 107e6, 15: 103e6, 16: 90e6, 17: 84e6, 18: 80e6,
  19: 59e6, 20: 64e6, 21: 47e6, 22: 51e6,
};

function getCumulativePosition(chr: number, bp: number): number {
  let offset = 0;
  for (let c = 1; c < chr; c++) {
    offset += CHR_LENGTHS[c] || 0;
  }
  return offset + bp;
}

interface Props {
  disorders: DisorderMeta[];
}

export function ManhattanPlot({ disorders }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [datasets, setDatasets] = useState<ManhattanData[]>([]);

  const addDisorder = (name: string) => {
    if (selected.length < 3 && !selected.includes(name)) {
      setSelected([...selected, name]);
    }
  };

  const removeDisorder = (name: string) => {
    setSelected(selected.filter((s) => s !== name));
  };

  useEffect(() => {
    if (selected.length === 0) {
      setDatasets([]);
      return;
    }
    Promise.all(selected.map((name) => loadManhattanData(name))).then(setDatasets);
  }, [selected]);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;

    const containerWidth = containerRef.current.offsetWidth;
    const width = containerWidth;
    const height = Math.max(400, Math.min(550, containerWidth * 0.4));
    const margin = { top: 24, right: 24, bottom: 56, left: 64 };

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const totalGenome = Object.values(CHR_LENGTHS).reduce((a, b) => a + b, 0);

    const x = d3.scaleLinear()
      .domain([0, totalGenome])
      .range([margin.left, width - margin.right]);

    const allNeglog = datasets.flatMap((d) => d.snps.map((s) => s.neglog10p));
    const maxY = Math.max(15, d3.max(allNeglog) || 15);

    const y = d3.scaleLinear()
      .domain([0, maxY])
      .range([height - margin.bottom, margin.top]);

    // Chromosome boundaries and labels
    let chrOffset = 0;
    for (let chr = 1; chr <= 22; chr++) {
      const len = CHR_LENGTHS[chr] || 0;
      const mid = chrOffset + len / 2;

      if (chr % 2 === 0) {
        svg.append("rect")
          .attr("x", x(chrOffset))
          .attr("y", margin.top)
          .attr("width", x(chrOffset + len) - x(chrOffset))
          .attr("height", height - margin.top - margin.bottom)
          .attr("fill", "#27272a")
          .attr("opacity", 0.3);
      }

      svg.append("text")
        .attr("x", x(mid))
        .attr("y", height - margin.bottom + 28)
        .attr("text-anchor", "middle")
        .attr("fill", "#52525b")
        .attr("font-size", "11px")
        .attr("font-family", "var(--font-geist-mono), monospace")
        .text(chr);

      chrOffset += len;
    }

    // Genome-wide significance line
    const gwasLine = -Math.log10(5e-8);
    svg.append("line")
      .attr("x1", margin.left)
      .attr("x2", width - margin.right)
      .attr("y1", y(gwasLine))
      .attr("y2", y(gwasLine))
      .attr("stroke", "#ef4444")
      .attr("stroke-dasharray", "6,4")
      .attr("opacity", 0.5)
      .attr("stroke-width", 1.5);

    // Significance label
    svg.append("text")
      .attr("x", width - margin.right - 4)
      .attr("y", y(gwasLine) - 6)
      .attr("text-anchor", "end")
      .attr("fill", "#ef4444")
      .attr("opacity", 0.5)
      .attr("font-size", "10px")
      .attr("font-family", "var(--font-geist-mono), monospace")
      .text("p = 5e-8");

    // Y axis
    svg.append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(6))
      .call((g) => g.select(".domain").remove())
      .call((g) => g.selectAll(".tick line").attr("stroke", "#27272a").attr("x2", width - margin.left - margin.right).attr("opacity", 0.5))
      .call((g) =>
        g.selectAll(".tick text")
          .attr("fill", "#71717a")
          .attr("font-family", "var(--font-geist-mono), monospace")
          .attr("font-size", "11px")
      );

    // Y label
    svg.append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -(height / 2))
      .attr("y", 16)
      .attr("text-anchor", "middle")
      .attr("fill", "#71717a")
      .attr("font-size", "12px")
      .attr("font-family", "var(--font-geist-mono), monospace")
      .text("-log\u2081\u2080(p)");

    // Plot points
    datasets.forEach((dataset) => {
      const meta = disorders.find((d) => d.name === dataset.disorder);
      const color = meta?.color || "#888";

      svg.selectAll(null)
        .data(dataset.snps)
        .join("circle")
        .attr("cx", (d) => x(getCumulativePosition(d.chr, d.bp)))
        .attr("cy", (d) => y(d.neglog10p))
        .attr("r", (d) => (d.neglog10p > gwasLine ? 3 : 2))
        .attr("fill", color)
        .attr("opacity", (d) => (d.neglog10p > gwasLine ? 0.85 : 0.5));
    });
  }, [datasets, disorders]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Select onValueChange={(v: string | null) => v && addDisorder(v)}>
          <SelectTrigger className="w-64 border-zinc-700/60 bg-zinc-900/60">
            <SelectValue placeholder="Add disorder (max 3)" />
          </SelectTrigger>
          <SelectContent>
            {disorders.map((d) => (
              <SelectItem key={d.name} value={d.name} disabled={selected.includes(d.name)}>
                <div className="flex items-center gap-2">
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: d.color }}
                  />
                  {d.name}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex flex-wrap gap-2">
          {selected.map((name) => {
            const meta = disorders.find((d) => d.name === name);
            return (
              <Badge
                key={name}
                variant="outline"
                className="cursor-pointer gap-1.5 border-zinc-700/60 px-3 py-1 text-sm transition-colors hover:border-zinc-600"
                onClick={() => removeDisorder(name)}
              >
                <div
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: meta?.color }}
                />
                <span style={{ color: meta?.color }}>{name}</span>
                <span className="text-zinc-600">x</span>
              </Badge>
            );
          })}
        </div>
      </div>
      <div ref={containerRef} className="overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/30 p-4">
        {selected.length === 0 ? (
          <div className="flex h-[400px] items-center justify-center">
            <p className="text-sm text-zinc-600">Select up to 3 disorders to overlay their Manhattan plots</p>
          </div>
        ) : (
          <svg ref={svgRef} className="w-full" />
        )}
      </div>
    </div>
  );
}
