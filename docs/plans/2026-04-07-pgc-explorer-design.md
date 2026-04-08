# PGC Explorer — Design Document

## Overview

Interactive visualization tool for cross-disorder psychiatric genetics analysis using Psychiatric Genomics Consortium (PGC) GWAS summary statistics from HuggingFace (`OpenMed/pgc-*` datasets). Over 1 billion rows across 12 disorder groups and 52 publications.

## Goals

- Explore genetic overlaps across psychiatric disorders
- Provide reproducible Jupyter notebooks others can run
- Build an interactive web frontend for visualization
- Start with pre-computed snapshots (static JSON), evolve to live queries later if needed

## Architecture

```
pgc-explorer/
├── notebooks/           # Jupyter — data loading, processing, exploration
│   ├── 01_load_data.ipynb
│   ├── 02_cross_disorder_correlations.ipynb
│   ├── 03_shared_loci.ipynb
│   └── 04_export_snapshots.ipynb
├── data/                # Generated snapshots (gitignored)
│   ├── correlation_matrix.json
│   ├── manhattan/       # Per-disorder chromosome-level summary stats
│   ├── network_graph.json
│   └── metadata.json
├── web/                 # Next.js frontend
│   ├── app/
│   │   ├── page.tsx            # Landing — overview + key stats
│   │   ├── correlations/       # Heatmap view
│   │   ├── manhattan/          # Multi-disorder Manhattan overlay
│   │   └── network/            # Network graph view
│   └── public/data/            # Snapshot JSONs copied here at build
├── scripts/             # CLI helpers
├── requirements.txt
└── context.md
```

**Data flow:** HuggingFace → Notebooks (process 1B+ rows with Polars) → JSON snapshots → Next.js static imports → Interactive charts

## Stack

### Python Pipeline
- `datasets` — HuggingFace data loader
- `polars` — fast DataFrame processing for 1B+ rows
- `scipy.stats` — genetic correlation computation
- `numpy` — matrix operations
- Jupyter notebooks for reproducibility

### Next.js Frontend
- `D3.js` — Manhattan plots (fine control for dense genomic data)
- `react-plotly.js` — correlation heatmap (interactive hover, zoom)
- `react-force-graph` — network graph (force-directed, draggable)
- `shadcn/ui` — layout, cards, controls
- Tailwind CSS — styling
- Dark mode default

## Views

### 1. Landing Page (`/`)
Hero with project description, key stats (12 disorders, 52 publications, 1B+ rows), cards linking to each visualization.

### 2. Correlation Heatmap (`/correlations`)
- 12x12 matrix of genetic correlations between disorders
- Diverging color scale (red = positive, blue = negative)
- Hover: exact rg value, p-value, source publication
- Click cell: shows shared top loci between that disorder pair

### 3. Manhattan Overlay (`/manhattan`)
- Multi-disorder Manhattan plot
- Dropdown to select 2-3 disorders to overlay (different colors)
- X-axis: chromosomal position, Y-axis: -log10(p)
- Genome-wide significance line at 5e-8
- Pre-computed top SNPs (p < 1e-5) to keep JSON manageable
- Zoom into individual chromosomes

### 4. Network Graph (`/network`)
- Disorders as nodes (sized by number of significant loci)
- Edges weighted by genetic correlation (thicker = stronger)
- Force-directed layout, related disorders cluster naturally
- Color-coded by disorder category
- Click node to highlight connections

## Data Scale Strategy

Pre-computed snapshots approach:
- Python pipeline runs locally, crunches 1B+ rows into aggregated JSON
- Correlation matrix: ~144 cells (12x12)
- Manhattan data: top SNPs only (p < 1e-5), ~100K-500K points per disorder
- Network graph: 12 nodes, ~66 edges
- Total frontend data: estimated 50-200MB JSON
- Future: add DuckDB live query endpoint for drill-down (Phase 2)

## Cost

- $0 — static files on Vercel free tier
- Compute cost: local machine running Python pipeline
